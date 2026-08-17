"""Hierarquia base de exceções de domínio.

Features herdam destas pra criar exceções mais específicas, p.ex.:

    class CredenciaisInvalidas(ErroValidacao): ...
    class UsuarioJaExiste(ConflitoEstado): ...

A camada de transporte (`routes.py`) traduz cada classe num status HTTP
apropriado — services e domínio NÃO conhecem códigos HTTP.
"""

from __future__ import annotations


class ErroDominio(Exception):
    def __init__(self, mensagem: str, *, detalhes: dict | None = None) -> None:
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.detalhes: dict = detalhes or {}


class ErroValidacao(ErroDominio):
    """Entrada inválida ou estado semântico inconsistente (400/422)."""


class RecursoNaoEncontrado(ErroDominio):
    """Recurso pedido não existe (404)."""


class ConflitoEstado(ErroDominio):
    """Conflito com o estado atual (409). Ex.: e-mail já cadastrado."""


class NaoAutorizado(ErroDominio):
    """Falta de credenciais válidas (401)."""


class AcessoNegado(ErroDominio):
    """Credenciais válidas, mas sem permissão pro recurso (403)."""


class FalhaInfraestrutura(ErroDominio):
    """Falha em infra externa: banco, HTTP, storage, IA (500/503)."""
