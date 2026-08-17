"""Entry point do backend FastAPI.

Composition root: monta `Settings`, constrói o container e cria a aplicação.
Lifespan event cria as tabelas SQLModel no startup (ver ADR-0006).

Rodar localmente:
    uvicorn src.main:app --reload
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlmodel import SQLModel

# Garante que os modelos SQLModel sejam registrados em SQLModel.metadata
# antes de chamar create_all.
import src.auth.domain.models  # noqa: F401
import src.temas.domain.models  # noqa: F401
import src.videos.domain.models  # noqa: F401
from src.auth import criar_router as criar_router_auth
from src.config import Settings
from src.container import Container, construir_container
from src.shared.logging import configurar_logging
from src.temas import criar_router as criar_router_temas
from src.videos import criar_router as criar_router_videos


def criar_app() -> FastAPI:
    settings = Settings()
    configurar_logging(settings.log_level)
    container: Container = construir_container(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        SQLModel.metadata.create_all(container.engine())
        yield

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )
    app.state.container = container
    app.state.settings = settings

    if settings.cors_origins or settings.cors_origin_regex:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_origin_regex=settings.cors_origin_regex or None,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["*"],
            # Sem isso, o app não consegue ler X-Token-Expired (browsers
            # escondem headers customizados em CORS).
            expose_headers=["X-Token-Expired", "Content-Range", "Accept-Ranges"],
        )

    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(criar_router_auth(container, limiter), prefix="/auth", tags=["auth"])
    app.include_router(criar_router_temas(container), prefix="/temas", tags=["temas"])
    app.include_router(criar_router_videos(container), prefix="/videos", tags=["videos"])

    return app


app = criar_app()
