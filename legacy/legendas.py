"""
Transcrição e geração de legendas como overlays PNG (sem libass).

Por que PNG e não .ass?
  - O ffmpeg distribuído pelo Homebrew (`brew install ffmpeg`) costuma vir
    compilado SEM `libass`, o que faz os filtros `subtitles=` e `ass=`
    simplesmente não existirem nesse build. Em vez de exigir reinstalação
    do ffmpeg, rasterizamos a legenda em PNGs transparentes via Pillow e
    aplicamos com o filtro `overlay=` — que existe em qualquer ffmpeg.

  - `transcrever(audio)` usa faster-whisper para timestamps word-level.

  - `gerar_overlays_legenda(palavras, pasta_saida)` agrupa em blocos de
    2-4 palavras e produz um PNG por grupo. Retorna a lista que
    `montar_video` consome para construir a cascata de overlays no
    filter_complex.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont
from faster_whisper import WhisperModel


# =========================================================================
# Estilo padrão das legendas
# =========================================================================
ESTILO_DEFAULT = {
    "tamanho_fonte": 58,                     # tamanho-alvo (reduzido p/ caber)
    "tamanho_fonte_minimo": 36,              # piso quando o auto-fit reduz
    "cor_texto": (255, 255, 255, 255),       # branco opaco
    "cor_contorno": (0, 0, 0, 255),          # preto opaco
    "espessura_contorno": 5,
    "palavras_por_grupo": 5,                 # texto por bloco na tela
    "palavras_por_linha": 3,                 # quebra em 2 linhas se passar disso
    "espacamento_entre_linhas": 12,          # px entre as duas linhas
    "margem_horizontal": 80,                 # px de respiro nas laterais
    "espacamento_vertical": 18,              # px de respiro acima/abaixo do texto
}

# Resolução-base do vídeo final.
LARGURA_VIDEO = 1080
ALTURA_VIDEO = 1920

# Lista ordenada de candidatos a fonte — primeira que existir é usada.
CANDIDATOS_FONTE = [
    "/System/Library/Fonts/Supplemental/Arial Black.ttf",     # macOS
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",      # macOS
    "/System/Library/Fonts/HelveticaNeue.ttc",                # macOS
    "/Library/Fonts/Arial Black.ttf",                         # macOS antigo
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",   # Linux
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",               # Arch
]


# =========================================================================
# Transcrição
# =========================================================================
def transcrever(caminho_audio: Path) -> list[dict]:
    """
    Transcreve o áudio retornando lista de palavras com timestamps.

    Returns:
        [{"palavra": str, "inicio": float, "fim": float}, ...]
    """
    if not caminho_audio.exists():
        raise FileNotFoundError(caminho_audio)

    modelo_nome = os.environ.get("WHISPER_MODEL", "base")
    modelo = WhisperModel(modelo_nome, device="cpu", compute_type="int8")

    segments, _info = modelo.transcribe(
        str(caminho_audio),
        language="pt",
        word_timestamps=True,
        vad_filter=False,
    )

    palavras: list[dict] = []
    for seg in segments:
        if not seg.words:
            continue
        for w in seg.words:
            texto = (w.word or "").strip()
            if not texto:
                continue
            palavras.append({
                "palavra": texto,
                "inicio": float(w.start),
                "fim": float(w.end),
            })

    if not palavras:
        raise RuntimeError("Whisper não produziu nenhuma palavra com timestamp")

    return palavras


# =========================================================================
# Renderização PNG via Pillow
# =========================================================================
def _localizar_arquivo_fonte() -> Optional[str]:
    """Retorna o primeiro candidato de fonte que existe no disco (ou None)."""
    for caminho in CANDIDATOS_FONTE:
        if os.path.exists(caminho):
            return caminho
    return None


def _carregar_fonte(caminho: Optional[str], tamanho: int) -> ImageFont.ImageFont:
    """Carrega a fonte do caminho dado no tamanho dado; cai para default se preciso."""
    if caminho:
        try:
            return ImageFont.truetype(caminho, tamanho)
        except OSError:
            pass
    return ImageFont.load_default()


def _quebrar_em_linhas(palavras_texto: list[str], max_por_linha: int) -> str:
    """
    Quebra a lista de palavras em até 2 linhas, distribuindo de forma
    aproximadamente equilibrada.

    Ex.: ["o", "filho", "pediu", "a", "herança"] com max_por_linha=3
         → "O FILHO PEDIU\\nA HERANÇA"
    """
    n = len(palavras_texto)
    if n <= max_por_linha:
        return " ".join(palavras_texto)
    # Equilibra: tenta dividir mais ou menos no meio, sem ultrapassar
    # max_por_linha na primeira linha.
    corte = min(max_por_linha, (n + 1) // 2)
    linha1 = " ".join(palavras_texto[:corte])
    linha2 = " ".join(palavras_texto[corte:])
    return f"{linha1}\n{linha2}"


def _ajustar_fonte_para_caber(
    texto: str,
    caminho_fonte: Optional[str],
    estilo: dict,
    largura_max: int,
) -> ImageFont.ImageFont:
    """
    Devolve a maior fonte (entre `tamanho_fonte` e `tamanho_fonte_minimo`)
    para a qual nenhuma linha de `texto` ultrapassa `largura_max`,
    considerando o contorno. Se nem o tamanho mínimo couber, retorna o
    mínimo mesmo assim.
    """
    dummy_img = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    dummy_draw = ImageDraw.Draw(dummy_img)

    alvo = estilo["tamanho_fonte"]
    minimo = estilo["tamanho_fonte_minimo"]
    stroke = estilo["espessura_contorno"]

    for tamanho in range(alvo, minimo - 1, -2):
        fonte = _carregar_fonte(caminho_fonte, tamanho)
        bbox = dummy_draw.multiline_textbbox(
            (0, 0), texto, font=fonte, stroke_width=stroke, align="center",
            spacing=estilo["espacamento_entre_linhas"],
        )
        if (bbox[2] - bbox[0]) <= largura_max:
            return fonte

    return _carregar_fonte(caminho_fonte, minimo)


def _renderizar_png(
    texto: str,
    caminho_fonte: Optional[str],
    estilo: dict,
    caminho_saida: Path,
) -> None:
    """
    Renderiza `texto` (1 ou 2 linhas, separadas por `\\n`) em um PNG
    transparente, centralizado horizontalmente, com auto-fit de fonte.
    """
    largura_util = LARGURA_VIDEO - 2 * estilo["margem_horizontal"]
    fonte = _ajustar_fonte_para_caber(texto, caminho_fonte, estilo, largura_util)
    spacing = estilo["espacamento_entre_linhas"]

    dummy = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    draw_dummy = ImageDraw.Draw(dummy)
    bbox = draw_dummy.multiline_textbbox(
        (0, 0), texto, font=fonte,
        stroke_width=estilo["espessura_contorno"],
        align="center", spacing=spacing,
    )
    largura_texto = bbox[2] - bbox[0]
    altura_texto = bbox[3] - bbox[1]

    largura_canvas = LARGURA_VIDEO
    altura_canvas = altura_texto + 2 * estilo["espacamento_vertical"]

    img = Image.new("RGBA", (largura_canvas, altura_canvas), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    x = (largura_canvas - largura_texto) // 2 - bbox[0]
    y = estilo["espacamento_vertical"] - bbox[1]

    draw.multiline_text(
        (x, y),
        texto,
        font=fonte,
        fill=estilo["cor_texto"],
        stroke_width=estilo["espessura_contorno"],
        stroke_fill=estilo["cor_contorno"],
        align="center",
        spacing=spacing,
    )

    img.save(caminho_saida, "PNG")


def _grupos(palavras: list[dict], tamanho: int) -> list[list[dict]]:
    """Divide a lista de palavras em blocos consecutivos de até `tamanho`."""
    return [palavras[i:i + tamanho] for i in range(0, len(palavras), tamanho)]


def gerar_overlays_legenda(
    palavras: list[dict],
    pasta_saida: Path,
    estilo: Optional[dict] = None,
) -> list[dict]:
    """
    Renderiza um PNG por grupo de palavras e devolve a lista de overlays.

    Returns:
        [{"png": Path, "inicio": float, "fim": float, "texto": str}, ...]
        — ordenada cronologicamente. `inicio` é o tempo da primeira palavra
        do grupo, `fim` é o tempo da última. Entre grupos pode haver gap
        (silêncio ou respiro), tratado naturalmente pelo overlay com
        `enable=between(...)`.
    """
    if not palavras:
        raise ValueError("Lista de palavras vazia")

    est = {**ESTILO_DEFAULT, **(estilo or {})}
    pasta_saida.mkdir(parents=True, exist_ok=True)
    caminho_fonte = _localizar_arquivo_fonte()
    if caminho_fonte is None:
        print(
            "  [legendas] AVISO: nenhuma fonte TTF do sistema encontrada, "
            "usando a default do Pillow (texto pode ficar muito pequeno)."
        )

    overlays: list[dict] = []
    for i, grupo in enumerate(_grupos(palavras, est["palavras_por_grupo"]), start=1):
        palavras_upper = [w["palavra"].strip().upper() for w in grupo if w["palavra"].strip()]
        if not palavras_upper:
            continue
        texto = _quebrar_em_linhas(palavras_upper, est["palavras_por_linha"])

        png_path = pasta_saida / f"legenda_{i:03d}.png"
        _renderizar_png(texto, caminho_fonte, est, png_path)

        overlays.append({
            "png": png_path,
            "inicio": grupo[0]["inicio"],
            "fim": grupo[-1]["fim"],
            "texto": texto,
        })

    return overlays


# =========================================================================
# Teste rápido isolado
# =========================================================================
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Uso: python -m src.legendas <caminho_audio.mp3>")
        sys.exit(1)

    audio = Path(sys.argv[1])
    print(f"Transcrevendo {audio}...")
    palavras = transcrever(audio)
    print(f"OK: {len(palavras)} palavras")

    pasta = audio.parent / "legendas_png"
    overlays = gerar_overlays_legenda(palavras, pasta)
    print(f"{len(overlays)} overlays gerados em {pasta}")
    for ov in overlays[:3]:
        print(f"  {ov['inicio']:.2f}-{ov['fim']:.2f}: {ov['texto']!r} → {ov['png'].name}")
