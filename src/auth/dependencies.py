"""Dependências FastAPI da feature `auth`.

Padrão: cada função `construir_<algo>(container)` retorna uma callable
que pode ser usada com `Depends(...)`. Isso mantém o composition root em
`main.py`/`container.py` enquanto deixa as rotas declarativas.
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from src.auth.domain.exceptions import TokenExpirado, UsuarioInativo
from src.auth.domain.models import Usuario
from src.auth.security import TokenInvalido
from src.auth.service import AuthService
from src.container import Container


_bearer = HTTPBearer(auto_error=True)


def construir_get_session(container: Container) -> Callable[[], Generator[Session, None, None]]:
    def _get_session() -> Generator[Session, None, None]:
        factory = container.session_factory()
        sessao = factory()
        try:
            yield sessao
        finally:
            sessao.close()

    return _get_session


def construir_get_auth_service(
    container: Container,
    get_session: Callable[[], Generator[Session, None, None]],
) -> Callable[..., AuthService]:
    def _get_auth_service(session: Session = Depends(get_session)) -> AuthService:
        return container.auth_service(session)

    return _get_auth_service


def construir_usuario_atual(
    container: Container,
    get_session: Callable[[], Generator[Session, None, None]],
) -> Callable[..., Usuario]:
    """Retorna a dependency `usuario_atual` real, com closure no container.

    Erros de expiração devolvem 401 com `X-Token-Expired: true` (sinal pro
    app disparar refresh automático). Qualquer outro erro vira 401 simples.
    """

    def _usuario_atual(
        credenciais: HTTPAuthorizationCredentials = Depends(_bearer),
        session: Session = Depends(get_session),
    ) -> Usuario:
        token = credenciais.credentials
        jwt_service = container.jwt_service()
        try:
            payload = jwt_service.decodificar(token)
        except TokenExpirado:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expirado",
                headers={"X-Token-Expired": "true", "WWW-Authenticate": "Bearer"},
            )
        except TokenInvalido:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Carrega o usuário via repo direto pra não montar AuthService completo aqui.
        from src.auth.data.repository_sqlmodel import UsuarioRepositorySqlModel
        usuario = UsuarioRepositorySqlModel(session).buscar_por_id(payload.sub)
        if usuario is None or not usuario.ativo:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuário inativo",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return usuario

    return _usuario_atual


def extrair_metadados_request(request: Request) -> tuple[str | None, str | None]:
    """Devolve (ip, user_agent) — usados pra auditoria leve de refresh tokens."""
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    return ip, ua
