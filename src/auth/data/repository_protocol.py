"""Interfaces (Protocols) dos repositórios da feature `auth`.

O `AuthService` consome apenas estes Protocols. Implementações concretas
ficam em `repository_sqlmodel.py`. Trocar SQLModel por outra coisa é só
criar uma nova implementação que atenda o mesmo contrato.
"""

from __future__ import annotations

from typing import Protocol

from src.auth.domain.models import RefreshToken, Usuario


class UsuarioRepositoryProtocol(Protocol):
    def criar(self, usuario: Usuario) -> Usuario: ...

    def buscar_por_email(self, email: str) -> Usuario | None: ...

    def buscar_por_id(self, usuario_id: str) -> Usuario | None: ...

    def atualizar(self, usuario: Usuario) -> Usuario: ...


class RefreshTokenRepositoryProtocol(Protocol):
    def criar(self, token: RefreshToken) -> RefreshToken: ...

    def buscar_por_hash(self, token_hash: str) -> RefreshToken | None: ...

    def revogar_por_id(
        self,
        token_id: str,
        *,
        motivo: str,
        substituido_por_id: str | None = None,
    ) -> None: ...

    def revogar_todos_ativos_do_usuario(
        self,
        usuario_id: str,
        *,
        motivo: str,
    ) -> int:
        """Revoga todos os refresh tokens não-expirados e não-revogados do usuário.

        Retorna o número de tokens revogados.
        """
        ...

    def atualizar_ultimo_uso(self, token_id: str) -> None: ...
