"""Endpoints HTTP da feature `temas`.

Rotas públicas (catálogo). Não exigem autenticação. Apenas serializam
o registry estático — sem lógica de negócio (ADR-0002).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from src.container import Container
from src.temas.domain.exceptions import TemaNaoEncontrado
from src.temas.registry import listar_temas, obter_tema
from src.temas.schemas import ListarTemasResponse, TemaResponse


def criar_router(container: Container) -> APIRouter:  # noqa: ARG001
    router = APIRouter()

    @router.get("", response_model=ListarTemasResponse)
    def listar() -> ListarTemasResponse:
        return ListarTemasResponse(
            temas=[TemaResponse.de_provider(p) for p in listar_temas()]
        )

    @router.get("/{tema_id}", response_model=TemaResponse)
    def detalhar(tema_id: str) -> TemaResponse:
        try:
            provider = obter_tema(tema_id)
        except TemaNaoEncontrado as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, exc.mensagem)
        return TemaResponse.de_provider(provider)

    return router
