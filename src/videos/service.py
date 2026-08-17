"""VideosService — coordena criação/consulta de jobs.

A execução do pipeline em si fica no `PipelineOrchestrator`. Este
service só:
- valida tema_id contra o registry
- aplica limite de jobs paralelos globais
- cria o registro de Job e devolve o orchestrator-callback que o caller
  (rota) deve agendar em BackgroundTasks
- expõe consultas com autorização cross-user
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from src.pipeline import EntradaPipeline, PipelineOrchestrator
from src.temas import HistoriaEscolhida, Registry
from src.videos.data.repository_protocol import JobRepositoryProtocol
from src.videos.domain.entities import StatusJob
from src.videos.domain.exceptions import (
    AcessoNegadoJob,
    JobNaoConcluido,
    JobNaoEncontrado,
    LimiteJobsParalelos,
    TemaInvalido,
)
from src.videos.domain.models import Job


def _agora() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class VideosService:
    def __init__(
        self,
        job_repo: JobRepositoryProtocol,
        temas_registry: Registry,
        orquestrador: PipelineOrchestrator,
        max_jobs_paralelos: int,
        logger: logging.Logger | None = None,
    ) -> None:
        self._repo = job_repo
        self._registry = temas_registry
        self._orq = orquestrador
        self._max_paralelos = max_jobs_paralelos
        self._log = logger or logging.getLogger(__name__)

    # ----- Comandos -----

    def criar_job(
        self,
        *,
        usuario_id: str,
        tema_id: str,
        voz_tts: str | None = None,
        num_cenas: int = 6,
    ) -> Job:
        try:
            self._registry.obter(tema_id)
        except Exception:
            raise TemaInvalido(tema_id=tema_id)

        ativos = self._repo.contar_ativos_global()
        if ativos >= self._max_paralelos:
            raise LimiteJobsParalelos(max_paralelos=self._max_paralelos)

        job = Job(
            usuario_id=usuario_id,
            tema_id=tema_id,
            voz_tts=voz_tts,
            num_cenas=num_cenas,
            status=StatusJob.PENDENTE.value,
        )
        return self._repo.criar(job)

    def executar_em_background(self, job_id: str) -> None:
        """Função chamada via BackgroundTasks — roda o pipeline inteiro.

        Captura qualquer exceção e marca o job como `falhou` com mensagem.
        """
        job = self._repo.buscar_por_id(job_id)
        if job is None:
            self._log.error("Job %s desapareceu antes de executar", job_id)
            return

        provider = self._registry.obter(job.tema_id)
        historia = provider.escolher_historia(ids_recentes=[])  # TODO: tracking de recentes por usuário
        entrada = EntradaPipeline(
            job_id=job.id,
            provider_tema=provider,
            historia=historia,
            voz_tts=job.voz_tts,
            num_cenas=job.num_cenas,
        )

        job.iniciado_em = _agora()
        job.status = StatusJob.PROCESSANDO.value
        self._repo.atualizar(job)

        def callback(etapa: str, progresso: int) -> None:
            atual = self._repo.buscar_por_id(job_id)
            if atual is None:
                return
            atual.etapa_atual = etapa
            atual.progresso_pct = progresso
            self._repo.atualizar(atual)

        try:
            resultado = self._orq.executar(entrada, callback)
        except Exception as exc:
            self._log.exception("Pipeline falhou pro job %s", job_id)
            atual = self._repo.buscar_por_id(job_id)
            if atual is not None:
                atual.status = StatusJob.FALHOU.value
                atual.erro = f"{type(exc).__name__}: {exc}"[:1000]
                atual.concluido_em = _agora()
                self._repo.atualizar(atual)
            return

        atual = self._repo.buscar_por_id(job_id)
        if atual is None:
            return
        atual.status = StatusJob.CONCLUIDO.value
        atual.etapa_atual = "finalizado"
        atual.progresso_pct = 100
        atual.titulo = resultado.titulo
        atual.subtitulo = resultado.subtitulo
        atual.roteiro = resultado.roteiro
        atual.duracao_segundos = resultado.duracao_segundos
        atual.caminho_arquivo = str(resultado.caminho_video)
        atual.caminho_thumbnail = (
            str(resultado.caminho_thumbnail) if resultado.caminho_thumbnail else None
        )
        atual.tamanho_bytes = resultado.tamanho_bytes
        atual.creditos_json = json.dumps(resultado.creditos, ensure_ascii=False)
        atual.legenda = resultado.post.legenda
        atual.hashtags_json = json.dumps(resultado.post.hashtags, ensure_ascii=False)
        atual.concluido_em = _agora()
        self._repo.atualizar(atual)

    # ----- Consultas (com autorização cross-user) -----

    def obter_para_usuario(self, job_id: str, usuario_id: str) -> Job:
        job = self._repo.buscar_por_id(job_id)
        if job is None:
            raise JobNaoEncontrado(job_id=job_id)
        if job.usuario_id != usuario_id:
            raise AcessoNegadoJob()
        return job

    def obter_caminho_arquivo(self, job_id: str, usuario_id: str) -> Path:
        job = self.obter_para_usuario(job_id, usuario_id)
        if job.status != StatusJob.CONCLUIDO.value or not job.caminho_arquivo:
            raise JobNaoConcluido(status=job.status)
        return Path(job.caminho_arquivo)

    def obter_caminho_thumbnail(self, job_id: str, usuario_id: str) -> Path:
        job = self.obter_para_usuario(job_id, usuario_id)
        if not job.caminho_thumbnail:
            raise JobNaoConcluido(status=job.status)
        return Path(job.caminho_thumbnail)

    def listar(
        self,
        usuario_id: str,
        *,
        limit: int = 20,
        offset: int = 0,
        tema_id: str | None = None,
        apenas_concluidos: bool = True,
    ) -> tuple[list[Job], int]:
        jobs = self._repo.listar_do_usuario(
            usuario_id,
            limit=limit,
            offset=offset,
            tema_id=tema_id,
            apenas_concluidos=apenas_concluidos,
        )
        total = self._repo.contar_do_usuario(
            usuario_id, tema_id=tema_id, apenas_concluidos=apenas_concluidos
        )
        return jobs, total
