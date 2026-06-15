"""Entidades de domínio do pipeline de geração de vídeos.

Tipos leves usados pelos Protocols. Independentes de SQLModel/Pydantic
pra manter o domínio livre de infra.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Roteiro:
    titulo: str
    texto: str
    palavras: int


@dataclass(frozen=True)
class Cena:
    ordem: int
    trecho_texto: str
    query_pexels: str
    descricao_visual: str


@dataclass
class Narracao:
    caminho_audio: Path
    duracao_segundos: float


@dataclass(frozen=True)
class PalavraTranscrita:
    palavra: str
    inicio: float
    fim: float


@dataclass(frozen=True)
class OverlayLegenda:
    png: Path
    inicio: float
    fim: float
    texto: str


@dataclass
class CenaComStock:
    """Cena enriquecida com o vídeo baixado e créditos da Pexels."""

    cena: Cena
    caminho_arquivo: Path | None
    pexels_id: int | None = None
    pexels_url: str = ""
    fotografo_nome: str = ""
    fotografo_url: str = ""


@dataclass(frozen=True)
class Post:
    """Texto pronto pra colar na descrição da publicação + hashtags."""

    legenda: str
    hashtags: list[str]


@dataclass
class ResultadoPipeline:
    """O que o orchestrator devolve ao final de tudo dar certo."""

    titulo: str
    subtitulo: str
    roteiro: str
    caminho_video: Path
    caminho_thumbnail: Path | None
    duracao_segundos: float
    tamanho_bytes: int
    post: Post
    creditos: list[dict] = field(default_factory=list)
