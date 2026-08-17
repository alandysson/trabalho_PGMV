"""Implementações SQLModel dos repositórios da feature `auth`.

Cada instância é construída com uma `Session` por request — não fazer
singleton. O ciclo de vida da sessão é gerenciado pela dependency
`get_session` em `routes`/`dependencies`.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from src.auth.domain.exceptions import UsuarioJaExiste
from src.auth.domain.models import RefreshToken, Usuario


def _agora() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class UsuarioRepositorySqlModel:
    def __init__(self, session: Session) -> None:
        self._session = session

    def criar(self, usuario: Usuario) -> Usuario:
        self._session.add(usuario)
        try:
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise UsuarioJaExiste(email=usuario.email) from exc
        self._session.refresh(usuario)
        return usuario

    def buscar_por_email(self, email: str) -> Usuario | None:
        stmt = select(Usuario).where(Usuario.email == email)
        return self._session.exec(stmt).first()

    def buscar_por_id(self, usuario_id: str) -> Usuario | None:
        return self._session.get(Usuario, usuario_id)

    def atualizar(self, usuario: Usuario) -> Usuario:
        usuario.atualizado_em = _agora()
        self._session.add(usuario)
        self._session.commit()
        self._session.refresh(usuario)
        return usuario


class RefreshTokenRepositorySqlModel:
    def __init__(self, session: Session) -> None:
        self._session = session

    def criar(self, token: RefreshToken) -> RefreshToken:
        self._session.add(token)
        self._session.commit()
        self._session.refresh(token)
        return token

    def buscar_por_hash(self, token_hash: str) -> RefreshToken | None:
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        return self._session.exec(stmt).first()

    def revogar_por_id(
        self,
        token_id: str,
        *,
        motivo: str,
        substituido_por_id: str | None = None,
    ) -> None:
        token = self._session.get(RefreshToken, token_id)
        if token is None or token.revogado:
            return
        token.revogado = True
        token.revogado_em = _agora()
        token.motivo_revogacao = motivo
        if substituido_por_id is not None:
            token.substituido_por_id = substituido_por_id
        self._session.add(token)
        self._session.commit()

    def revogar_todos_ativos_do_usuario(
        self,
        usuario_id: str,
        *,
        motivo: str,
    ) -> int:
        agora = _agora()
        stmt = select(RefreshToken).where(
            RefreshToken.usuario_id == usuario_id,
            RefreshToken.revogado == False,  # noqa: E712 (SQLModel exige ==)
            RefreshToken.expira_em > agora,
        )
        tokens = list(self._session.exec(stmt).all())
        for t in tokens:
            t.revogado = True
            t.revogado_em = agora
            t.motivo_revogacao = motivo
            self._session.add(t)
        self._session.commit()
        return len(tokens)

    def atualizar_ultimo_uso(self, token_id: str) -> None:
        token = self._session.get(RefreshToken, token_id)
        if token is None:
            return
        token.ultimo_uso_em = _agora()
        self._session.add(token)
        self._session.commit()
