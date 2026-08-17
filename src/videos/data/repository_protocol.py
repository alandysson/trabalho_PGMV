"""Interface do repositório de jobs."""

from __future__ import annotations

from typing import Protocol

from src.videos.domain.models import Job


class JobRepositoryProtocol(Protocol):
    def criar(self, job: Job) -> Job: ...

    def buscar_por_id(self, job_id: str) -> Job | None: ...

    def atualizar(self, job: Job) -> Job: ...

    def listar_do_usuario(
        self,
        usuario_id: str,
        *,
        limit: int,
        offset: int,
        tema_id: str | None = None,
        apenas_concluidos: bool = True,
    ) -> list[Job]: ...

    def contar_do_usuario(
        self,
        usuario_id: str,
        *,
        tema_id: str | None = None,
        apenas_concluidos: bool = True,
    ) -> int: ...

    def contar_ativos_global(self) -> int:
        """Conta jobs com status `pendente` ou `processando` (todos usuários)."""
        ...
