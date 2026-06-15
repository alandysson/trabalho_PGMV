"""Exceções específicas do domínio de autenticação.

Herdam de `src.shared.exceptions` para que a camada de routes possa mapear
cada classe ao status HTTP apropriado sem o domínio conhecer HTTP.
"""

from __future__ import annotations

from src.shared.exceptions import (
    ConflitoEstado,
    ErroValidacao,
    NaoAutorizado,
)


class CredenciaisInvalidas(NaoAutorizado):
    """Email/senha não conferem. Resposta genérica para não revelar existência de conta."""

    def __init__(self) -> None:
        super().__init__("Credenciais inválidas")


class UsuarioJaExiste(ConflitoEstado):
    """Tentativa de registrar e-mail já cadastrado."""

    def __init__(self, email: str) -> None:
        super().__init__("E-mail já cadastrado", detalhes={"email": email})


class TokenExpirado(NaoAutorizado):
    """JWT ou refresh token expirado por tempo."""

    def __init__(self) -> None:
        super().__init__("Token expirado")


class TokenRevogado(NaoAutorizado):
    """Refresh token marcado como revogado (logout, troca de senha, etc.)."""

    def __init__(self) -> None:
        super().__init__("Token revogado")


class PossivelInvasaoDetectada(NaoAutorizado):
    """Refresh token já revogado foi reutilizado.

    Indica que pode haver um atacante tentando usar um token antigo.
    O service revoga TODOS os refresh tokens ativos do usuário antes de
    lançar essa exceção.
    """

    def __init__(self, usuario_id: str) -> None:
        super().__init__(
            "Sessão invalidada por segurança",
            detalhes={"usuario_id": usuario_id},
        )


class UsuarioInativo(NaoAutorizado):
    """Usuário existe mas está marcado como inativo / banido."""

    def __init__(self) -> None:
        super().__init__("Usuário inativo")


class SenhaAtualIncorreta(ErroValidacao):
    """Em PATCH /auth/eu, a `senha_atual` informada não bate."""

    def __init__(self) -> None:
        super().__init__("Senha atual incorreta")
