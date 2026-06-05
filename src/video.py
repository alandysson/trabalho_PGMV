"""
Composição do vídeo final via FFmpeg (subprocess).

Pipeline interno:

  1. Calcula a duração que cada clipe deve ocupar (proporcional ao número
     de palavras do trecho que cobre).
  2. Para cada clipe da Pexels, gera um "clipe normalizado":
       - Corta no comprimento alvo (loop se o stock for muito curto).
       - Recorta/escala para 1080x1920 (cover) — preserva enquadramento.
       - Aplica Ken Burns leve (zoompan) para dar movimento.
  3. Concatena os clipes normalizados em um único arquivo de vídeo.
  4. Mixa o áudio: narração em volume cheio + música de fundo bem baixa.
  5. Aplica as legendas como cascata de overlays PNG (um por grupo de
     palavras), com `enable=between(t,...)` controlando quando aparece.
  6. Codifica saída H.264 + AAC, 1080x1920@30fps, ~6Mbps.

Por que overlays PNG e não `ass=`?
  O `ffmpeg` do Homebrew costuma vir sem `libass`, e os filtros de
  subtítulo deixam de existir nesse build. A cascata de overlays usa
  apenas o filtro `overlay=`, disponível em qualquer ffmpeg.

Se uma cena vier sem `caminho_arquivo` (busca Pexels falhou), ela é
substituída por um fundo preto da mesma duração — pipeline não trava.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .narracao import duracao_audio


LARGURA = 1080
ALTURA = 1920
FPS = 30
BITRATE_VIDEO = "6M"
BITRATE_AUDIO = "192k"

# Volume relativo: narração mantém, música fica bem ao fundo.
DB_NARRACAO = 0
DB_MUSICA = -25

# Posição vertical da legenda: terço inferior (margem inferior em pixels).
LEGENDA_MARGEM_INFERIOR = 300


def _ffmpeg(args: list[str]) -> None:
    """Executa ffmpeg silenciosamente; em erro, imprime stderr e re-lança."""
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            "FFmpeg falhou.\n"
            f"Comando: {' '.join(cmd)}\n"
            f"Stderr: {proc.stderr}"
        )


def _verificar_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "ffmpeg não encontrado no PATH. Instale via 'brew install ffmpeg' "
            "(macOS) ou 'apt install ffmpeg' (Linux)."
        )


def _normalizar_clipe(
    entrada: Path | None,
    duracao_s: float,
    saida: Path,
) -> Path:
    """
    Gera um clipe de `duracao_s` segundos em 1080x1920@30fps, sem áudio,
    preservando o MOVIMENTO original do vídeo stock.

    Se `entrada` é None, produz um fundo preto.
    Se o stock é mais curto que a duração alvo, faz loop.
    """
    if entrada is None:
        args = [
            "-f", "lavfi",
            "-i", f"color=c=black:s={LARGURA}x{ALTURA}:r={FPS}:d={duracao_s:.3f}",
            "-an",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium",
            "-b:v", BITRATE_VIDEO,
            str(saida),
        ]
        _ffmpeg(args)
        return saida

    # Apenas escala + crop centralizado (cover) + força fps.
    # IMPORTANTE: NÃO usar `zoompan` aqui — ele foi feito para imagens
    # estáticas e, em vídeo, congela no primeiro frame transformando o
    # clipe em slideshow.
    vf = (
        f"scale={LARGURA}:{ALTURA}:force_original_aspect_ratio=increase,"
        f"crop={LARGURA}:{ALTURA},"
        f"setsar=1,"
        f"fps={FPS}"
    )

    args = [
        "-stream_loop", "-1",
        "-i", str(entrada),
        "-t", f"{duracao_s:.3f}",
        "-vf", vf,
        "-an",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium",
        "-b:v", BITRATE_VIDEO,
        str(saida),
    ]
    _ffmpeg(args)
    return saida


def _concatenar(clipes: list[Path], saida: Path) -> Path:
    """Concatena os clipes normalizados via demuxer concat (rápido, sem reencode).

    Atenção: o demuxer `concat` interpreta paths relativos à pasta DO ARQUIVO
    DE LISTA, não ao cwd. Por isso passamos paths absolutos.
    """
    lista = saida.with_suffix(".txt")
    with open(lista, "w", encoding="utf-8") as f:
        for c in clipes:
            f.write(f"file '{c.resolve().as_posix()}'\n")

    args = [
        "-f", "concat", "-safe", "0",
        "-i", str(lista),
        "-c", "copy",
        str(saida),
    ]
    _ffmpeg(args)
    lista.unlink(missing_ok=True)
    return saida


def _construir_filter_complex(
    overlays_legenda: list[dict],
    idx_primeiro_overlay: int,
    tem_musica: bool,
) -> tuple[str, str]:
    """
    Monta a string de filter_complex e devolve (string, label_video_final).

    Cada overlay é aplicado em cadeia sobre o vídeo:
      [0:v][2:v]overlay=...:enable='between(t,...)'[v0];
      [v0][3:v]overlay=...:enable='between(t,...)'[v1];
      ...

    O áudio entra como filtro paralelo (narração ou mix com música).
    """
    filtros: list[str] = []
    ultimo_label = "0:v"

    for i, ov in enumerate(overlays_legenda):
        input_idx = idx_primeiro_overlay + i
        novo_label = f"v{i}"
        y_pos = f"H-h-{LEGENDA_MARGEM_INFERIOR}"
        filtros.append(
            f"[{ultimo_label}][{input_idx}:v]"
            f"overlay=x=(W-w)/2:y={y_pos}"
            f":enable='between(t,{ov['inicio']:.3f},{ov['fim']:.3f})'"
            f"[{novo_label}]"
        )
        ultimo_label = novo_label

    if tem_musica:
        filtros.append(f"[1:a]volume={DB_NARRACAO}dB[a1]")
        filtros.append(f"[2:a]volume={DB_MUSICA}dB[a2]")
        filtros.append(
            "[a1][a2]amix=inputs=2:duration=first:dropout_transition=0[a]"
        )
    else:
        filtros.append(f"[1:a]volume={DB_NARRACAO}dB[a]")

    return ";".join(filtros), ultimo_label


def montar_video(
    cenas: list[dict],
    audio_narracao: Path,
    overlays_legenda: list[dict],
    musica_fundo: Path | None,
    caminho_saida: Path,
) -> Path:
    """
    Monta o vídeo final.

    Args:
        cenas: lista de cenas com `trecho_texto` e `caminho_arquivo` (Path|None).
        audio_narracao: MP3 da narração principal.
        overlays_legenda: lista produzida por `legendas.gerar_overlays_legenda`.
                          Cada item: {"png": Path, "inicio": float, "fim": float}.
                          Pode ser lista vazia (vídeo sai sem legendas).
        musica_fundo: MP3 instrumental ou None (sem música).
        caminho_saida: MP4 final.
    """
    _verificar_ffmpeg()

    if not cenas:
        raise ValueError("Nenhuma cena para compor")
    if not audio_narracao.exists():
        raise FileNotFoundError(audio_narracao)

    caminho_saida.parent.mkdir(parents=True, exist_ok=True)
    pasta_trabalho = caminho_saida.parent / "_compose"
    pasta_trabalho.mkdir(exist_ok=True)

    dur_total = duracao_audio(audio_narracao)

    # 1) Distribui duração entre cenas proporcionalmente às palavras.
    palavras_por_cena = [
        max(1, len((c.get("trecho_texto") or "").split())) for c in cenas
    ]
    total_palavras = sum(palavras_por_cena)
    duracoes = [dur_total * (p / total_palavras) for p in palavras_por_cena]

    # 2) Normaliza cada clipe.
    clipes_normalizados: list[Path] = []
    for i, (cena, dur) in enumerate(zip(cenas, duracoes), start=1):
        entrada = cena.get("caminho_arquivo")
        if entrada is not None and not Path(entrada).exists():
            entrada = None
        saida_clipe = pasta_trabalho / f"clipe_{i:02d}.mp4"
        _normalizar_clipe(
            Path(entrada) if entrada else None, dur, saida_clipe
        )
        clipes_normalizados.append(saida_clipe)

    # 3) Concatena os clipes em um único vídeo intermediário.
    video_concat = pasta_trabalho / "concat.mp4"
    _concatenar(clipes_normalizados, video_concat)

    # 4) Monta a invocação final do ffmpeg com a cascata de overlays.
    args: list[str] = ["-i", str(video_concat), "-i", str(audio_narracao)]
    proximo_idx = 2

    tem_musica = musica_fundo is not None and musica_fundo.exists()
    if tem_musica:
        args.extend(["-stream_loop", "-1", "-i", str(musica_fundo)])
        proximo_idx = 3

    idx_primeiro_overlay = proximo_idx
    # Cada PNG entra como "still" loopada pela duração total — assim o
    # `enable=between(...)` controla a visibilidade sem se preocupar com
    # o tempo interno de cada input.
    for ov in overlays_legenda:
        args.extend([
            "-loop", "1",
            "-t", f"{dur_total:.3f}",
            "-i", str(ov["png"]),
        ])

    filter_complex, label_v_final = _construir_filter_complex(
        overlays_legenda, idx_primeiro_overlay, tem_musica
    )

    # Caso degenerado: sem overlays nenhum, mapeia direto a entrada do vídeo.
    if not overlays_legenda:
        map_v = "0:v"
    else:
        map_v = f"[{label_v_final}]"

    args.extend([
        "-filter_complex", filter_complex,
        "-map", map_v, "-map", "[a]",
        "-t", f"{dur_total:.3f}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium",
        "-b:v", BITRATE_VIDEO, "-r", str(FPS),
        "-c:a", "aac", "-b:a", BITRATE_AUDIO,
        "-shortest",
        str(caminho_saida),
    ])

    _ffmpeg(args)

    # Limpa pasta de trabalho.
    shutil.rmtree(pasta_trabalho, ignore_errors=True)

    return caminho_saida


# =========================================================================
# Teste rápido isolado
# =========================================================================
if __name__ == "__main__":
    print("Este módulo é melhor testado pelo pipeline completo (src.main).")
    _verificar_ffmpeg()
    print("ffmpeg disponível no PATH ✓")
