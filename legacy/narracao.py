"""
Módulo de narração (TTS).

Usa `edge-tts` (biblioteca assíncrona que conversa com o serviço de voz
neural da Microsoft Edge) para sintetizar o roteiro em um arquivo MP3.

A voz é configurável via env (`TTS_VOICE`), com padrão masculino sério
em pt-BR — adequado ao tom de histórias bíblicas.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import edge_tts
from mutagen.mp3 import MP3


# Voz padrão se a env não estiver setada.
VOZ_DEFAULT = "pt-BR-AntonioNeural"


async def _sintetizar(texto: str, caminho_saida: Path, voz: str, rate: str) -> None:
    """Coroutine interna que faz o stream do edge-tts para arquivo."""
    comunicado = edge_tts.Communicate(text=texto, voice=voz, rate=rate)
    await comunicado.save(str(caminho_saida))


def gerar_audio(
    texto: str,
    caminho_saida: Path,
    voz: str | None = None,
    rate: str = "+0%",
) -> Path:
    """
    Sintetiza `texto` em MP3 usando edge-tts.

    Args:
        texto: o roteiro completo a ser narrado.
        caminho_saida: onde gravar o MP3 (a pasta-pai deve existir).
        voz: nome da voz edge-tts (ex.: "pt-BR-AntonioNeural"). Se None,
             usa env TTS_VOICE ou o default.
        rate: ajuste de velocidade no formato edge-tts ("+0%", "-10%", etc.).
              "+0%" é o ritmo natural — recomendado para histórias bíblicas.

    Returns:
        O Path do arquivo gerado.
    """
    if not texto.strip():
        raise ValueError("Texto vazio passado para gerar_audio")

    voz_final = voz or os.environ.get("TTS_VOICE", VOZ_DEFAULT)
    caminho_saida.parent.mkdir(parents=True, exist_ok=True)

    asyncio.run(_sintetizar(texto, caminho_saida, voz_final, rate))

    if not caminho_saida.exists() or caminho_saida.stat().st_size == 0:
        raise RuntimeError(
            f"edge-tts não gerou áudio válido em {caminho_saida}"
        )

    return caminho_saida


def duracao_audio(caminho: Path) -> float:
    """
    Retorna a duração do arquivo MP3 em segundos.

    Usa `mutagen` (puro Python, sem precisar chamar ffprobe).
    """
    if not caminho.exists():
        raise FileNotFoundError(caminho)
    audio = MP3(str(caminho))
    return float(audio.info.length)


# =========================================================================
# Teste rápido isolado
# =========================================================================
if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    saida = Path("/tmp/teste_narracao.mp3")
    texto_teste = (
        "Você sabia que um pastorzinho derrotou um gigante com uma única pedra? "
        "Essa é a história de Davi e Golias."
    )
    print(f"Gerando narração de teste em {saida}...")
    gerar_audio(texto_teste, saida)
    dur = duracao_audio(saida)
    print(f"OK. Duração: {dur:.2f}s")
