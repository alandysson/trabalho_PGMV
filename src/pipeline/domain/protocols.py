"""Protocols (interfaces) do pipeline de geração.

Consolidados num arquivo só porque são todos consumidos pelo
`orchestrator` e formam um grupo coeso. As implementações concretas
ficam em `src/pipeline/adapters/`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from src.pipeline.domain.entities import (
    Cena,
    CenaComStock,
    Narracao,
    OverlayLegenda,
    PalavraTranscrita,
    Post,
    Roteiro,
)


class RoteiroGeneratorProtocol(Protocol):
    def gerar_roteiro(
        self,
        *,
        titulo: str,
        referencia: str,
        personagens: list[str],
        tema_central: str,
        system_prompt: str,
    ) -> Roteiro: ...

    def gerar_cenas(
        self,
        *,
        roteiro: str,
        num_cenas: int,
        dicas_visuais: str,
    ) -> list[Cena]: ...

    def gerar_post(
        self,
        *,
        titulo: str,
        referencia: str,
        tema_central: str,
        tema_nome: str,
        roteiro: str,
    ) -> Post: ...


class TtsProviderProtocol(Protocol):
    def gerar(self, *, texto: str, caminho_saida: Path, voz: str | None = None) -> Narracao: ...


class TranscriptionProtocol(Protocol):
    def transcrever(self, *, caminho_audio: Path) -> list[PalavraTranscrita]: ...

    def gerar_overlays_legenda(
        self,
        *,
        palavras: list[PalavraTranscrita],
        pasta_saida: Path,
    ) -> list[OverlayLegenda]: ...


class StockVideoProtocol(Protocol):
    def buscar_e_baixar(
        self,
        *,
        cenas: list[Cena],
        pasta_saida: Path,
    ) -> list[CenaComStock]: ...


class VideoComposerProtocol(Protocol):
    def compor(
        self,
        *,
        cenas: list[CenaComStock],
        audio_narracao: Path,
        overlays: list[OverlayLegenda],
        musica_fundo: Path | None,
        caminho_saida: Path,
    ) -> Path: ...

    def gerar_thumbnail(self, *, caminho_video: Path, caminho_saida: Path) -> Path: ...


class StorageProtocol(Protocol):
    def pasta_de_job(self, job_id: str) -> Path: ...

    def caminho_video_final(self, job_id: str) -> Path: ...

    def caminho_thumbnail(self, job_id: str) -> Path: ...

    def musica_aleatoria(self) -> Path | None: ...
