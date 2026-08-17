"""Schemas Pydantic da feature `auth` (DTOs HTTP).

Separados dos modelos de domínio. Validações de formato e regras simples
(força mínima de senha, comprimento de nome) vivem aqui — regras de
negócio (e-mail único, comparação de hash) vivem no `AuthService`.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator
from typing_extensions import Self

from src.auth.domain.models import Usuario


# ----- helpers -----

_MSG_SENHA_FRACA = (
    "Senha deve ter ao menos 8 caracteres, incluindo pelo menos 1 letra e 1 número."
)


def _validar_senha_forte(valor: str) -> str:
    if len(valor) < 8:
        raise ValueError(_MSG_SENHA_FRACA)
    if not any(c.isalpha() for c in valor):
        raise ValueError(_MSG_SENHA_FRACA)
    if not any(c.isdigit() for c in valor):
        raise ValueError(_MSG_SENHA_FRACA)
    return valor


# ----- requests -----

class RegistrarRequest(BaseModel):
    email: EmailStr
    senha: str
    nome: str = Field(min_length=2, max_length=100)

    @field_validator("senha")
    @classmethod
    def _v_senha(cls, v: str) -> str:
        return _validar_senha_forte(v)


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class AtualizarPerfilRequest(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=100)
    senha_atual: str | None = Field(default=None, min_length=1)
    senha_nova: str | None = Field(default=None)

    @field_validator("senha_nova")
    @classmethod
    def _v_senha_nova(cls, v: str | None) -> str | None:
        return _validar_senha_forte(v) if v is not None else v

    @model_validator(mode="after")
    def _v_coerencia(self) -> Self:
        if self.senha_nova is not None and self.senha_atual is None:
            raise ValueError("senha_atual é obrigatória ao informar senha_nova")
        if self.nome is None and self.senha_nova is None:
            raise ValueError("nada a atualizar: informe nome ou senha_nova")
        return self


# ----- responses -----

class UsuarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    nome: str
    criado_em: datetime


class AuthTokensResponse(BaseModel):
    usuario: UsuarioResponse
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "bearer"


class TokensResponse(BaseModel):
    """Resposta do /refresh — sem o usuário, só os tokens."""

    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "bearer"


class EuResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    nome: str
    criado_em: datetime
    videos_gerados: int = 0  # TODO: popular quando a feature `videos` existir.

    @classmethod
    def de_usuario(cls, usuario: Usuario, *, videos_gerados: int = 0) -> "EuResponse":
        return cls(
            id=usuario.id,
            email=usuario.email,
            nome=usuario.nome,
            criado_em=usuario.criado_em,
            videos_gerados=videos_gerados,
        )
