"""Adapter para transcrição via faster-whisper + overlays PNG via Pillow.

Delega ao `legacy/legendas.py`. O modelo Whisper é carregado pela primeira
vez sob demanda (cache em `~/.cache/huggingface/`).
"""

from __future__ import annotations

import os
from pathlib import Path

from legacy.legendas import gerar_overlays_legenda as _gerar_overlays
from legacy.legendas import transcrever as _transcrever
from src.pipeline.domain.entities import OverlayLegenda, PalavraTranscrita


class WhisperTranscription:
    def __init__(self, modelo: str = "base") -> None:
        # O legacy lê WHISPER_MODEL do env; setamos pra propagar o
        # parâmetro vindo de Settings sem mexer no legacy.
        os.environ["WHISPER_MODEL"] = modelo
        self._modelo = modelo

    def transcrever(self, *, caminho_audio: Path) -> list[PalavraTranscrita]:
        brutos = _transcrever(caminho_audio)
        return [
            PalavraTranscrita(palavra=b["palavra"], inicio=b["inicio"], fim=b["fim"])
            for b in brutos
        ]

    def gerar_overlays_legenda(
        self,
        *,
        palavras: list[PalavraTranscrita],
        pasta_saida: Path,
    ) -> list[OverlayLegenda]:
        # Converte de volta pro formato dict que o legacy espera.
        brutos_palavras = [
            {"palavra": p.palavra, "inicio": p.inicio, "fim": p.fim}
            for p in palavras
        ]
        brutos_overlays = _gerar_overlays(brutos_palavras, pasta_saida)
        return [
            OverlayLegenda(
                png=o["png"], inicio=o["inicio"], fim=o["fim"], texto=o["texto"]
            )
            for o in brutos_overlays
        ]
