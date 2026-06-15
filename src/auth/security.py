"""Primitivas de segurança do módulo `auth`.

Define Protocols (HashService, JwtService) e implementações concretas
baseadas em `passlib[bcrypt]` e `python-jose`. Também expõe funções puras
para gerar e hashear refresh tokens.

Outros módulos do `auth` consomem **apenas os Protocols** — manter este
arquivo como única fronteira com `passlib`/`jose` é o que permite trocar
implementações sem mexer no service.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Protocol

import bcrypt
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError

from src.auth.domain.entities import JwtPayload
from src.auth.domain.exceptions import TokenExpirado
from src.shared.exceptions import NaoAutorizado


# ----- Hash de senha -----

# bcrypt usa, por especificação, apenas os primeiros 72 bytes da senha.
# Truncamos explicitamente — bcrypt 4.x rejeita inputs maiores, e a versão
# anterior ignorava silenciosamente. Truncar evita erro sem mudar a
# semântica esperada por usuários (senhas com >72 bytes são raríssimas).
_BCRYPT_MAX_BYTES = 72


def _preparar_senha(senha: str) -> bytes:
    return senha.encode("utf-8")[:_BCRYPT_MAX_BYTES]


class HashServiceProtocol(Protocol):
    def hashear(self, senha: str) -> str: ...
    def verificar(self, senha: str, hash_armazenado: str) -> bool: ...


class BcryptHashService:
    """Implementação bcrypt direto (sem passlib).

    `rounds` controla o custo computacional. 12 é o padrão recomendado em
    2026 (latência ~250ms em hardware modesto, alto custo pra brute force).
    """

    def __init__(self, rounds: int = 12) -> None:
        self._rounds = rounds

    def hashear(self, senha: str) -> str:
        salt = bcrypt.gensalt(rounds=self._rounds)
        return bcrypt.hashpw(_preparar_senha(senha), salt).decode("utf-8")

    def verificar(self, senha: str, hash_armazenado: str) -> bool:
        try:
            return bcrypt.checkpw(_preparar_senha(senha), hash_armazenado.encode("utf-8"))
        except (ValueError, TypeError):
            return False


# ----- JWT -----

class TokenInvalido(NaoAutorizado):
    def __init__(self) -> None:
        super().__init__("Token inválido")


class JwtServiceProtocol(Protocol):
    def emitir_access(self, usuario_id: str, email: str) -> str: ...
    def decodificar(self, token: str) -> JwtPayload: ...


class JoseJwtService:
    """JWT HS256 via python-jose."""

    def __init__(
        self,
        secret: str,
        algorithm: str = "HS256",
        access_ttl_minutos: int = 15,
    ) -> None:
        if not secret:
            raise ValueError("JWT secret não pode ser vazio")
        self._secret = secret
        self._algorithm = algorithm
        self._access_ttl = timedelta(minutes=access_ttl_minutos)

    def emitir_access(self, usuario_id: str, email: str) -> str:
        agora = datetime.now(timezone.utc)
        payload = {
            "sub": usuario_id,
            "email": email,
            "iat": int(agora.timestamp()),
            "exp": int((agora + self._access_ttl).timestamp()),
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def decodificar(self, token: str) -> JwtPayload:
        try:
            raw = jwt.decode(token, self._secret, algorithms=[self._algorithm])
        except ExpiredSignatureError as exc:
            raise TokenExpirado() from exc
        except JWTError as exc:
            raise TokenInvalido() from exc

        try:
            return JwtPayload(
                sub=raw["sub"],
                email=raw["email"],
                exp=int(raw["exp"]),
                iat=int(raw["iat"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise TokenInvalido() from exc


# ----- Refresh tokens (funções puras) -----

_REFRESH_PREFIX = "rt_"


def gerar_refresh_token_plain() -> str:
    """Gera um refresh token opaco aleatório.

    Formato: ``rt_<48 bytes url-safe base64>``. Esse valor é o que vai pro
    cliente; no banco fica só `hashear_refresh_token(plain)`.
    """
    return f"{_REFRESH_PREFIX}{secrets.token_urlsafe(48)}"


def hashear_refresh_token(plain: str) -> str:
    """SHA-256 hex de um refresh token plain.

    Determinístico (sem salt) porque precisamos buscar o registro no banco
    pelo hash. A natureza opaca + alta entropia do token (>256 bits)
    compensa a falta de salt — não é dado tipo senha do usuário.
    """
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()
