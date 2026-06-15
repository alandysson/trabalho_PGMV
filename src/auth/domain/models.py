"""Modelos SQLModel da feature `auth`.

`Usuario` e `RefreshToken` são tabelas persistidas no banco. NUNCA
armazenamos refresh tokens em plain — `token_hash` guarda o SHA-256.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlmodel import Field, SQLModel


def _agora() -> datetime:
    # SQLite não preserva timezone — usamos UTC naive em toda a feature pra
    # garantir comparação consistente entre valores recém-criados e lidos do DB.
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _gerar_id_usuario() -> str:
    return f"u_{uuid4().hex[:12]}"


def _gerar_id_refresh() -> str:
    return f"rt_{uuid4().hex}"


class Usuario(SQLModel, table=True):
    __tablename__ = "usuarios"

    id: str = Field(default_factory=_gerar_id_usuario, primary_key=True)
    email: str = Field(unique=True, index=True, max_length=255)
    senha_hash: str = Field(max_length=255)
    nome: str = Field(max_length=100)
    criado_em: datetime = Field(default_factory=_agora)
    atualizado_em: datetime = Field(default_factory=_agora)
    ativo: bool = Field(default=True)
    email_verificado: bool = Field(default=False)


class RefreshToken(SQLModel, table=True):
    __tablename__ = "refresh_tokens"

    id: str = Field(default_factory=_gerar_id_refresh, primary_key=True)
    token_hash: str = Field(unique=True, index=True, max_length=64)
    usuario_id: str = Field(foreign_key="usuarios.id", index=True)

    criado_em: datetime = Field(default_factory=_agora)
    expira_em: datetime

    revogado: bool = Field(default=False)
    revogado_em: datetime | None = Field(default=None)
    motivo_revogacao: str | None = Field(default=None, max_length=32)
    substituido_por_id: str | None = Field(default=None)

    user_agent: str | None = Field(default=None, max_length=255)
    ip: str | None = Field(default=None, max_length=64)
    ultimo_uso_em: datetime | None = Field(default=None)
