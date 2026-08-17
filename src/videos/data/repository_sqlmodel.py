"""Implementação SQLModel do `JobRepository`."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Session, func, select

from src.videos.domain.entities import StatusJob
from src.videos.domain.models import Job


def _agora() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class JobRepositorySqlModel:
    def __init__(self, session: Session) -> None:
        self._session = session

    def criar(self, job: Job) -> Job:
        self._session.add(job)
        self._session.commit()
        self._session.refresh(job)
        return job

    def buscar_por_id(self, job_id: str) -> Job | None:
        return self._session.get(Job, job_id)

    def atualizar(self, job: Job) -> Job:
        job.atualizado_em = _agora()
        self._session.add(job)
        self._session.commit()
        self._session.refresh(job)
        return job

    def listar_do_usuario(
        self,
        usuario_id: str,
        *,
        limit: int,
        offset: int,
        tema_id: str | None = None,
        apenas_concluidos: bool = True,
    ) -> list[Job]:
        stmt = (
            select(Job)
            .where(Job.usuario_id == usuario_id)
            .order_by(Job.criado_em.desc())  # type: ignore[attr-defined]
            .offset(offset)
            .limit(limit)
        )
        if tema_id is not None:
            stmt = stmt.where(Job.tema_id == tema_id)
        if apenas_concluidos:
            stmt = stmt.where(Job.status == StatusJob.CONCLUIDO.value)
        return list(self._session.exec(stmt).all())

    def contar_do_usuario(
        self,
        usuario_id: str,
        *,
        tema_id: str | None = None,
        apenas_concluidos: bool = True,
    ) -> int:
        stmt = select(func.count()).select_from(Job).where(Job.usuario_id == usuario_id)
        if tema_id is not None:
            stmt = stmt.where(Job.tema_id == tema_id)
        if apenas_concluidos:
            stmt = stmt.where(Job.status == StatusJob.CONCLUIDO.value)
        return int(self._session.exec(stmt).one())

    def contar_ativos_global(self) -> int:
        stmt = (
            select(func.count())
            .select_from(Job)
            .where(Job.status.in_([StatusJob.PENDENTE.value, StatusJob.PROCESSANDO.value]))  # type: ignore[attr-defined]
        )
        return int(self._session.exec(stmt).one())
