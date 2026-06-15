"""DTOs internos do domínio de autenticação.

Tipos consumidos pelo `AuthService` ao retornar pares de tokens, ou ao
representar o payload decodificado de um JWT. NÃO confundir com `schemas.py`
(que define request/response HTTP).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AuthTokens:
    """Par de tokens emitido pelo backend.

    O `refresh_token_plain` é o valor enviado ao cliente — no banco fica só
    o SHA-256. NUNCA logar este campo.
    """

    access_token: str
    refresh_token_plain: str
    expires_in: int


@dataclass(frozen=True)
class JwtPayload:
    """Payload decodificado de um access token JWT."""

    sub: str
    email: str
    exp: int
    iat: int
