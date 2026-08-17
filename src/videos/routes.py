"""Endpoints HTTP da feature `videos`.

Todas as rotas exigem `usuario_atual`. Autorização cross-user é
verificada no service (não nas routes — DIP: routes só serializa).
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    status,
)
from fastapi.responses import FileResponse
from sqlmodel import Session

from src.auth import Usuario
from src.auth.dependencies import (
    construir_get_session,
    construir_usuario_atual,
)
from src.container import Container
from src.videos.domain.entities import StatusJob
from src.videos.domain.exceptions import (
    AcessoNegadoJob,
    JobNaoConcluido,
    JobNaoEncontrado,
    LimiteJobsParalelos,
    TemaInvalido,
)
from src.videos.schemas import (
    DetalhesVideoResponse,
    GerarVideoRequest,
    JobCriadoResponse,
    JobResumido,
    ListarVideosResponse,
    StatusJobResponse,
)
from src.videos.service import VideosService


def _agora() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def criar_router(container: Container) -> APIRouter:
    router = APIRouter()
    get_session = construir_get_session(container)
    usuario_atual = construir_usuario_atual(container, get_session)

    def get_service(session: Session = Depends(get_session)) -> VideosService:
        return container.videos_service(session)

    # ----- POST /videos/gerar -----

    @router.post(
        "/gerar",
        response_model=JobCriadoResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def gerar(
        body: GerarVideoRequest,
        background_tasks: BackgroundTasks,
        usuario: Usuario = Depends(usuario_atual),
        service: VideosService = Depends(get_service),
    ) -> JobCriadoResponse:
        prefs = body.preferencias
        try:
            job = service.criar_job(
                usuario_id=usuario.id,
                tema_id=body.tema_id,
                voz_tts=prefs.voz if prefs else None,
                num_cenas=(prefs.num_cenas if prefs and prefs.num_cenas else 6),
            )
        except TemaInvalido as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, exc.mensagem)
        except LimiteJobsParalelos as exc:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, exc.mensagem)

        # Agenda o pipeline pra rodar em background. O service vai abrir
        # sua própria session (não pode reutilizar a desta request — ela
        # fecha quando a resposta sai).
        background_tasks.add_task(_executar_em_background, container, job.id)

        return JobCriadoResponse(
            job_id=job.id,
            status=job.status,
            criado_em=job.criado_em,
            estimativa_segundos=120,
        )

    # ----- GET /videos/{job_id}/status -----

    @router.get("/{job_id}/status", response_model=StatusJobResponse)
    def consultar_status(
        job_id: str,
        usuario: Usuario = Depends(usuario_atual),
        service: VideosService = Depends(get_service),
    ) -> StatusJobResponse:
        job = _obter_ou_404(service, job_id, usuario.id)
        decorrido = None
        if job.iniciado_em is not None:
            fim = job.concluido_em or _agora()
            decorrido = int((fim - job.iniciado_em).total_seconds())
        return StatusJobResponse(
            job_id=job.id,
            status=job.status,
            etapa_atual=job.etapa_atual,
            progresso_pct=job.progresso_pct,
            tempo_decorrido_segundos=decorrido,
            erro=job.erro,
        )

    # ----- GET /videos/{job_id} -----

    @router.get("/{job_id}", response_model=DetalhesVideoResponse)
    def detalhes(
        job_id: str,
        usuario: Usuario = Depends(usuario_atual),
        service: VideosService = Depends(get_service),
    ) -> DetalhesVideoResponse:
        job = _obter_ou_404(service, job_id, usuario.id)
        if job.status != StatusJob.CONCLUIDO.value:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Job ainda não concluído (status: {job.status})",
            )
        return DetalhesVideoResponse.de_job(job)

    # ----- GET /videos/{job_id}/arquivo -----

    @router.get("/{job_id}/arquivo")
    def baixar_arquivo(
        job_id: str,
        usuario: Usuario = Depends(usuario_atual),
        service: VideosService = Depends(get_service),
    ) -> FileResponse:
        try:
            caminho = service.obter_caminho_arquivo(job_id, usuario.id)
        except JobNaoEncontrado as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, exc.mensagem)
        except AcessoNegadoJob as exc:
            raise HTTPException(status.HTTP_403_FORBIDDEN, exc.mensagem)
        except JobNaoConcluido as exc:
            raise HTTPException(status.HTTP_409_CONFLICT, exc.mensagem)

        if not caminho.exists():
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Arquivo de vídeo não encontrado")

        # FileResponse suporta HTTP Range nativamente (Starlette).
        return FileResponse(
            path=str(caminho),
            media_type="video/mp4",
            filename=f"{job_id}.mp4",
        )

    # ----- GET /videos/{job_id}/thumbnail -----

    @router.get("/{job_id}/thumbnail")
    def thumbnail(
        job_id: str,
        usuario: Usuario = Depends(usuario_atual),
        service: VideosService = Depends(get_service),
    ) -> FileResponse:
        try:
            caminho = service.obter_caminho_thumbnail(job_id, usuario.id)
        except JobNaoEncontrado as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, exc.mensagem)
        except AcessoNegadoJob as exc:
            raise HTTPException(status.HTTP_403_FORBIDDEN, exc.mensagem)
        except JobNaoConcluido as exc:
            raise HTTPException(status.HTTP_409_CONFLICT, exc.mensagem)

        if not caminho.exists():
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Thumbnail não encontrado")

        return FileResponse(
            path=str(caminho),
            media_type="image/jpeg",
            filename=f"{job_id}.jpg",
        )

    # ----- GET /videos -----

    @router.get("", response_model=ListarVideosResponse)
    def listar(
        usuario: Usuario = Depends(usuario_atual),
        service: VideosService = Depends(get_service),
        limit: int = Query(default=20, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        tema_id: str | None = Query(default=None),
        apenas_concluidos: bool = Query(default=True),
    ) -> ListarVideosResponse:
        jobs, total = service.listar(
            usuario.id,
            limit=limit,
            offset=offset,
            tema_id=tema_id,
            apenas_concluidos=apenas_concluidos,
        )
        return ListarVideosResponse(
            total=total,
            limit=limit,
            offset=offset,
            videos=[JobResumido.de_job(j) for j in jobs],
        )

    return router


# ----- Helpers internos -----

def _obter_ou_404(service: VideosService, job_id: str, usuario_id: str):
    try:
        return service.obter_para_usuario(job_id, usuario_id)
    except JobNaoEncontrado as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, exc.mensagem)
    except AcessoNegadoJob as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, exc.mensagem)


def _executar_em_background(container: Container, job_id: str) -> None:
    """Wrapper que abre nova sessão dedicada à task em background.

    A session da request original já foi fechada quando esta task roda;
    precisamos de uma sessão própria, longa o bastante pra cobrir o
    pipeline inteiro (1-3 min).
    """
    factory = container.session_factory()
    sessao = factory()
    try:
        service = container.videos_service(sessao)
        service.executar_em_background(job_id)
    finally:
        sessao.close()
