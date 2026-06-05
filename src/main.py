"""
Orquestrador da pipeline de vídeos bíblicos.

Executa em sequência as 8 etapas:
  [1/8] Escolha da história (Claude Haiku)
  [2/8] Roteiro narrável (Claude Sonnet)
  [3/8] Divisão em cenas + queries Pexels (Claude Sonnet)
  [4/8] Narração TTS (edge-tts)
  [5/8] Transcrição word-level (faster-whisper)
  [6/8] Busca e download de vídeos stock (Pexels)
  [7/8] Composição final (FFmpeg)
  [8/8] Notificação por e-mail (Gmail SMTP)

Cada execução cria uma pasta nova em `output/YYYY-MM-DD_HHMM/`, escreve
um `metadata.json` com tudo que foi feito e atualiza `historias_recentes.json`
na raiz do projeto (mantendo as últimas 20 histórias para evitar repetição).

Em caso de falha em qualquer etapa, envia e-mail de alerta com traceback
e re-lança a exceção (para o cron registrar não-zero exit status).
"""

from __future__ import annotations

import json
import random
import time
import traceback
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from .historias import escolher_historia
from .legendas import gerar_overlays_legenda, transcrever
from .narracao import duracao_audio, gerar_audio
from .notificacao import enviar_email_alerta, enviar_email_post
from .pexels import buscar_e_baixar_cenas
from .roteiro import gerar_cenas, gerar_post, gerar_roteiro
from .video import montar_video


# Carrega .env antes de qualquer leitura de env.
load_dotenv()

RAIZ = Path(__file__).resolve().parent.parent
PASTA_OUTPUT = RAIZ / "output"
PASTA_MUSICAS = RAIZ / "assets" / "music"
ARQUIVO_HISTORICO = RAIZ / "historias_recentes.json"
LIMITE_HISTORICO = 20
NUM_CENAS = 6


# =========================================================================
# Histórico de execuções
# =========================================================================
def _carregar_historico() -> list[str]:
    if not ARQUIVO_HISTORICO.exists():
        return []
    try:
        return json.loads(ARQUIVO_HISTORICO.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _salvar_historico(ids: list[str]) -> None:
    ARQUIVO_HISTORICO.write_text(
        json.dumps(ids, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _atualizar_historico(novo_id: str) -> None:
    atual = _carregar_historico()
    atual = [i for i in atual if i != novo_id]
    atual.append(novo_id)
    atual = atual[-LIMITE_HISTORICO:]
    _salvar_historico(atual)


# =========================================================================
# Música de fundo
# =========================================================================
def _sortear_musica() -> Path | None:
    """Sorteia um MP3 de assets/music. Retorna None se a pasta estiver vazia."""
    if not PASTA_MUSICAS.exists():
        return None
    candidatos = sorted(PASTA_MUSICAS.glob("*.mp3"))
    if not candidatos:
        return None
    return random.choice(candidatos)


# =========================================================================
# Pipeline principal
# =========================================================================
def executar() -> Path:
    """
    Executa a pipeline completa. Retorna o Path do MP4 final.
    Em caso de erro, envia alerta por e-mail e re-lança.
    """
    t0 = time.time()
    PASTA_OUTPUT.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    pasta = PASTA_OUTPUT / timestamp
    pasta.mkdir(parents=True, exist_ok=True)

    pasta_stock = pasta / "stock"
    pasta_stock.mkdir(exist_ok=True)

    metadata: dict = {
        "timestamp": timestamp,
        "pasta": str(pasta),
    }

    try:
        # ---------------- [1/8] Escolha da história ----------------
        print("[1/8] Escolhendo história...")
        recentes = _carregar_historico()
        historia = escolher_historia(historias_recentes=recentes)
        print(f"  → {historia['titulo']} ({historia['referencia']})")
        print(f"  motivo: {historia.get('motivo', '')}")
        metadata["historia"] = historia

        # ---------------- [2/8] Roteiro ----------------
        print("[2/8] Gerando roteiro (130-160 palavras)...")
        roteiro = gerar_roteiro(historia)
        print(f"  → {roteiro['palavras']} palavras | título: {roteiro['titulo']}")
        metadata["roteiro"] = roteiro

        # ---------------- [3/8] Cenas ----------------
        print(f"[3/8] Dividindo em cenas e gerando queries ({NUM_CENAS} cenas)...")
        cenas = gerar_cenas(roteiro["texto"], num_cenas=NUM_CENAS)
        for c in cenas:
            print(f"  cena {c['ordem']}: {c['query_pexels']}")
        metadata["cenas"] = cenas

        # Postagem (legenda + hashtags) — gerada cedo para falhar rápido.
        print("  gerando legenda e hashtags da postagem...")
        post = gerar_post(historia, roteiro)
        print(f"  → legenda: {post['legenda'][:80]}...")
        print(f"  → {len(post['hashtags'])} hashtags")
        metadata["post"] = post

        # ---------------- [4/8] Narração ----------------
        import os as _os
        voz = _os.environ.get("TTS_VOICE", "pt-BR-AntonioNeural")
        print(f"[4/8] Gerando narração com edge-tts (voz: {voz})...")
        audio_path = pasta / "narracao.mp3"
        gerar_audio(roteiro["texto"], audio_path)
        dur = duracao_audio(audio_path)
        print(f"  → {audio_path.name} ({dur:.2f}s)")
        metadata["voz"] = voz
        metadata["duracao_audio_s"] = dur

        # ---------------- [5/8] Transcrição + overlays PNG ----------------
        modelo_whisper = _os.environ.get("WHISPER_MODEL", "base")
        print(f"[5/8] Transcrevendo áudio com Whisper (modelo: {modelo_whisper})...")
        palavras = transcrever(audio_path)
        print(f"  → {len(palavras)} palavras com timestamps")
        pasta_legendas = pasta / "legendas"
        overlays_legenda = gerar_overlays_legenda(palavras, pasta_legendas)
        print(f"  → {len(overlays_legenda)} overlays PNG em {pasta_legendas.name}/")

        # ---------------- [6/8] Vídeos stock ----------------
        print(f"[6/8] Buscando vídeos no Pexels ({len(cenas)} cenas)...")
        cenas_com_video = buscar_e_baixar_cenas(cenas, pasta_stock)
        # Serializa caminhos como string para o JSON.
        cenas_meta = []
        creditos: list[str] = []
        for c in cenas_com_video:
            c_meta = {k: v for k, v in c.items() if k != "caminho_arquivo"}
            ca = c.get("caminho_arquivo")
            c_meta["caminho_arquivo"] = str(ca) if ca else None
            cenas_meta.append(c_meta)

            if c.get("fotografo_nome"):
                creditos.append(
                    f"Vídeo por {c['fotografo_nome']} (Pexels) - "
                    f"{c.get('pexels_url', '')}"
                )
        # Deduplica preservando ordem.
        creditos = list(dict.fromkeys(creditos))
        metadata["cenas"] = cenas_meta
        metadata["creditos_pexels"] = creditos

        # ---------------- [7/8] Composição ----------------
        print("[7/8] Compondo vídeo final com FFmpeg...")
        musica = _sortear_musica()
        if musica:
            print(f"  música de fundo: {musica.name}")
        else:
            print("  (sem música de fundo — assets/music/ vazio)")
        metadata["musica_fundo"] = musica.name if musica else None

        video_final = pasta / "video_final.mp4"
        montar_video(
            cenas=cenas_com_video,
            audio_narracao=audio_path,
            overlays_legenda=overlays_legenda,
            musica_fundo=musica,
            caminho_saida=video_final,
        )
        print(
            f"  → {video_final.name} "
            f"({video_final.stat().st_size / (1024 * 1024):.2f} MB)"
        )

        # ---------------- [8/8] E-mail ----------------
        print("[8/8] Enviando notificação por e-mail...")
        enviar_email_post(
            titulo_historia=historia["titulo"],
            referencia=historia["referencia"],
            roteiro=roteiro["texto"],
            creditos=creditos,
            video_path=video_final,
            post=post,
        )

        # ---------------- Persistência final ----------------
        tempo_total = time.time() - t0
        metadata["tempo_execucao_s"] = round(tempo_total, 2)
        (pasta / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        _atualizar_historico(historia["id"])

        print(f"✓ Concluído em {tempo_total:.1f}s. Vídeo: {video_final}")
        return video_final

    except Exception as e:
        tb = traceback.format_exc()
        print(f"❌ ERRO: {e}\n{tb}")
        # Tenta salvar o metadata parcial para debug.
        metadata["erro"] = str(e)
        metadata["traceback"] = tb
        try:
            (pasta / "metadata.json").write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass
        # Tenta notificar (não esconde a exceção original se o e-mail falhar).
        try:
            enviar_email_alerta(str(e) or e.__class__.__name__, tb)
        except Exception as ee:
            print(f"  (falha extra ao enviar alerta: {ee})")
        raise


if __name__ == "__main__":
    executar()
