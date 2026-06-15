"""Exceções específicas da feature `videos`."""

from __future__ import annotations

from src.shared.exceptions import (
    AcessoNegado,
    ConflitoEstado,
    ErroValidacao,
    RecursoNaoEncontrado,
)


class JobNaoEncontrado(RecursoNaoEncontrado):
    def __init__(self, job_id: str) -> None:
        super().__init__(f"Job '{job_id}' não encontrado", detalhes={"job_id": job_id})


class AcessoNegadoJob(AcessoNegado):
    """Usuário autenticado tentou acessar job de outro usuário."""

    def __init__(self) -> None:
        super().__init__("Acesso negado a este job")


class JobNaoConcluido(ConflitoEstado):
    """Tentativa de baixar arquivo de um job ainda em processamento."""

    def __init__(self, status: str) -> None:
        super().__init__(
            f"Job ainda não concluído (status: {status})",
            detalhes={"status": status},
        )


class LimiteJobsParalelos(ConflitoEstado):
    def __init__(self, max_paralelos: int) -> None:
        super().__init__(
            f"Limite de jobs em paralelo atingido ({max_paralelos}). Tente novamente em instantes.",
            detalhes={"max_paralelos": max_paralelos},
        )


class TemaInvalido(ErroValidacao):
    def __init__(self, tema_id: str) -> None:
        super().__init__(f"Tema '{tema_id}' inválido", detalhes={"tema_id": tema_id})
