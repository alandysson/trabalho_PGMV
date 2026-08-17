"""Modelo SQLModel da feature `videos`.

Cada `Job` é vinculado a um `usuario_id` (FK em `usuarios.id`). Filtros
e checagens de autorização cross-user usam essa coluna.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlmodel import Field, SQLModel


def _agora() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _gerar_id() -> str:
    return f"j_{uuid4().hex[:12]}"


class Job(SQLModel, table=True):
    __tablename__ = "jobs"

    id: str = Field(default_factory=_gerar_id, primary_key=True)
    usuario_id: str = Field(foreign_key="usuarios.id", index=True)
    tema_id: str = Field(index=True, max_length=64)

    status: str = Field(default="pendente", index=True, max_length=20)
    etapa_atual: str | None = Field(default=None, max_length=64)
    progresso_pct: int = Field(default=0)

    # Preferências do request original.
    voz_tts: str | None = Field(default=None, max_length=64)
    num_cenas: int = Field(default=6)

    # Preenchido conforme avança / termina.
    titulo: str | None = Field(default=None, max_length=200)
    subtitulo: str | None = Field(default=None, max_length=200)
    roteiro: str | None = Field(default=None)
    duracao_segundos: float | None = Field(default=None)

    caminho_arquivo: str | None = Field(default=None, max_length=500)
    caminho_thumbnail: str | None = Field(default=None, max_length=500)
    tamanho_bytes: int | None = Field(default=None)
    creditos_json: str | None = Field(default=None)

    # Legenda + hashtags prontas pra colar na descrição do post.
    legenda: str | None = Field(default=None)
    hashtags_json: str | None = Field(default=None)

    erro: str | None = Field(default=None)

    criado_em: datetime = Field(default_factory=_agora)
    atualizado_em: datetime = Field(default_factory=_agora)
    iniciado_em: datetime | None = Field(default=None)
    concluido_em: datetime | None = Field(default=None)
