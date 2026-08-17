"""Adapter para TTS via edge-tts.

Delega ao `legacy/narracao.py` (que é tema-agnóstico). Quando inlinarmos
o legacy/, a função `gerar_audio` migra pra cá direto.
"""

from __future__ import annotations

from pathlib import Path

from legacy.narracao import duracao_audio, gerar_audio
from src.pipeline.domain.entities import Narracao


class EdgeTtsProvider:
    def __init__(self, voz_padrao: str = "pt-BR-AntonioNeural") -> None:
        self._voz_padrao = voz_padrao

    def gerar(
        self,
        *,
        texto: str,
        caminho_saida: Path,
        voz: str | None = None,
    ) -> Narracao:
        voz_final = voz or self._voz_padrao
        gerar_audio(texto=texto, caminho_saida=caminho_saida, voz=voz_final)
        return Narracao(
            caminho_audio=caminho_saida,
            duracao_segundos=duracao_audio(caminho_saida),
        )
