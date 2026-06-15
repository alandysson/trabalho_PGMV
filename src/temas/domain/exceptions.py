"""Exceções específicas do domínio de temas."""

from __future__ import annotations

from src.shared.exceptions import RecursoNaoEncontrado


class TemaNaoEncontrado(RecursoNaoEncontrado):
    def __init__(self, tema_id: str) -> None:
        super().__init__(f"Tema '{tema_id}' não existe", detalhes={"tema_id": tema_id})


class CatalogoVazio(RecursoNaoEncontrado):
    """Disparada se um provider chamar `escolher_historia` mas o filtro de
    `ids_recentes` excluir todos os itens disponíveis."""

    def __init__(self, tema_id: str) -> None:
        super().__init__(
            f"Catálogo do tema '{tema_id}' não tem itens disponíveis após filtro",
            detalhes={"tema_id": tema_id},
        )
