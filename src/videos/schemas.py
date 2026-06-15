"""Schemas Pydantic da feature `videos`."""

from __future__ import annotations

import json
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.videos.domain.models import Job


# ----- Requests -----

class PreferenciasGeracao(BaseModel):
    voz: str | None = Field(default=None, max_length=64)
    duracao_alvo: int | None = Field(default=None, ge=15, le=180)
    num_cenas: int | None = Field(default=None, ge=3, le=10)


class GerarVideoRequest(BaseModel):
    tema_id: str
    preferencias: PreferenciasGeracao | None = None


# ----- Responses -----

class JobCriadoResponse(BaseModel):
    job_id: str
    status: str
    criado_em: datetime
    estimativa_segundos: int = 120


class StatusJobResponse(BaseModel):
    job_id: str
    status: str
    etapa_atual: str | None
    progresso_pct: int
    tempo_decorrido_segundos: int | None
    erro: str | None


class CreditoPexels(BaseModel):
    fotografo_nome: str = ""
    fotografo_url: str = ""
    pexels_url: str = ""


class DetalhesVideoResponse(BaseModel):
    job_id: str
    tema_id: str
    titulo: str | None
    subtitulo: str | None
    roteiro: str | None
    duracao_segundos: float | None
    criado_em: datetime
    url_arquivo: str
    url_thumbnail: str
    tamanho_bytes: int | None
    creditos: list[CreditoPexels] = Field(default_factory=list)
    legenda: str | None = None
    hashtags: list[str] = Field(default_factory=list)

    @classmethod
    def de_job(cls, job: Job) -> "DetalhesVideoResponse":
        creditos: list[CreditoPexels] = []
        if job.creditos_json:
            try:
                bruto = json.loads(job.creditos_json)
                creditos = [CreditoPexels(**c) for c in bruto if isinstance(c, dict)]
            except (json.JSONDecodeError, TypeError, ValueError):
                creditos = []
        hashtags: list[str] = []
        if job.hashtags_json:
            try:
                hashtags = [str(h) for h in json.loads(job.hashtags_json) if isinstance(h, str)]
            except (json.JSONDecodeError, TypeError, ValueError):
                hashtags = []
        return cls(
            job_id=job.id,
            tema_id=job.tema_id,
            titulo=job.titulo,
            subtitulo=job.subtitulo,
            roteiro=job.roteiro,
            duracao_segundos=job.duracao_segundos,
            criado_em=job.criado_em,
            url_arquivo=f"/videos/{job.id}/arquivo",
            url_thumbnail=f"/videos/{job.id}/thumbnail",
            tamanho_bytes=job.tamanho_bytes,
            creditos=creditos,
            legenda=job.legenda,
            hashtags=hashtags,
        )


class JobResumido(BaseModel):
    job_id: str
    titulo: str | None
    tema_id: str
    duracao_segundos: float | None
    status: str
    url_thumbnail: str
    criado_em: datetime

    @classmethod
    def de_job(cls, job: Job) -> "JobResumido":
        return cls(
            job_id=job.id,
            titulo=job.titulo,
            tema_id=job.tema_id,
            duracao_segundos=job.duracao_segundos,
            status=job.status,
            url_thumbnail=f"/videos/{job.id}/thumbnail",
            criado_em=job.criado_em,
        )


class ListarVideosResponse(BaseModel):
    total: int
    limit: int
    offset: int
    videos: list[JobResumido]
