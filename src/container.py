"""Container manual de Injeção de Dependências.

Composition root do backend. Ver ADR-0005 para o racional da escolha por um
container manual em vez de bibliotecas (`dependency-injector`, `punq`) ou de
apenas `Depends()` do FastAPI.

Convenção de escopo:
- **Singletons** (`HashService`, `JwtService`, `Engine`, `SessionFactory`):
  registrados via `register_singleton` — instanciados uma vez.
- **Per-request** (`AuthService`): expostos por método tipado que recebe
  a `Session` da request (vinda de uma dependency FastAPI). Resolve a
  necessidade de escopo por requisição sem expor sessões singleton.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, TypeVar

from src.config import Settings

if TYPE_CHECKING:
    from anthropic import Anthropic
    from sqlalchemy import Engine
    from sqlmodel import Session

    from src.auth.domain.contador_videos_protocol import ContadorVideosProtocol
    from src.auth.security import HashServiceProtocol, JwtServiceProtocol
    from src.auth.service import AuthService
    from src.pipeline import (
        PipelineOrchestrator,
        RoteiroGeneratorProtocol,
        StockVideoProtocol,
        StorageProtocol,
        TranscriptionProtocol,
        TtsProviderProtocol,
        VideoComposerProtocol,
    )
    from src.temas import Registry, SugeridorHistoriaProtocol
    from src.videos.service import VideosService

T = TypeVar("T")
Factory = Callable[["Container"], Any]


class Container:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._factories: dict[str, Factory] = {}
        self._singletons: dict[str, Any] = {}

    def register_singleton(self, key: str, factory: Factory) -> None:
        if key in self._factories:
            raise ValueError(f"Token já registrado: {key}")
        self._factories[key] = factory

    def resolve(self, key: str) -> Any:
        if key in self._singletons:
            return self._singletons[key]
        if key not in self._factories:
            raise KeyError(f"Token não registrado: {key}")
        instance = self._factories[key](self)
        self._singletons[key] = instance
        return instance

    # ----- Acessos tipados (singletons) -----

    def engine(self) -> "Engine":
        return self.resolve("Engine")

    def session_factory(self) -> Callable[[], "Session"]:
        return self.resolve("SessionFactory")

    def hash_service(self) -> "HashServiceProtocol":
        return self.resolve("HashService")

    def jwt_service(self) -> "JwtServiceProtocol":
        return self.resolve("JwtService")

    def anthropic_client(self) -> "Anthropic | None":
        return self.resolve("AnthropicClient")

    def sugeridor_historia(self) -> "SugeridorHistoriaProtocol | None":
        return self.resolve("SugeridorHistoria")

    def roteiro_generator(self) -> "RoteiroGeneratorProtocol":
        return self.resolve("RoteiroGenerator")

    def tts_provider(self) -> "TtsProviderProtocol":
        return self.resolve("TtsProvider")

    def transcription(self) -> "TranscriptionProtocol":
        return self.resolve("Transcription")

    def stock_video(self) -> "StockVideoProtocol":
        return self.resolve("StockVideo")

    def video_composer(self) -> "VideoComposerProtocol":
        return self.resolve("VideoComposer")

    def storage(self) -> "StorageProtocol":
        return self.resolve("Storage")

    def pipeline_orchestrator(self) -> "PipelineOrchestrator":
        return self.resolve("PipelineOrchestrator")

    # ----- Acessos tipados (per-request) -----

    def temas_registry(self, session: "Session") -> "Registry":
        from src.temas import construir_registry
        from src.temas.data.repository_sqlmodel import (
            HistoriaSugeridaRepositorySqlModel,
        )

        return construir_registry(
            sugeridor=self.sugeridor_historia(),
            historias_repo=HistoriaSugeridaRepositorySqlModel(session),
        )

    def videos_service(self, session: "Session") -> "VideosService":
        from src.videos.data.repository_sqlmodel import JobRepositorySqlModel
        from src.videos.service import VideosService

        return VideosService(
            job_repo=JobRepositorySqlModel(session),
            temas_registry=self.temas_registry(session),
            orquestrador=self.pipeline_orchestrator(),
            max_jobs_paralelos=self.settings.max_jobs_paralelos,
        )

    def contador_videos(self, session: "Session") -> "ContadorVideosProtocol":
        from src.videos.data.contador_sqlmodel import ContadorVideosViaJobRepo
        from src.videos.data.repository_sqlmodel import JobRepositorySqlModel

        return ContadorVideosViaJobRepo(JobRepositorySqlModel(session))

    def auth_service(self, session: "Session") -> "AuthService":
        from src.auth.data.repository_sqlmodel import (
            RefreshTokenRepositorySqlModel,
            UsuarioRepositorySqlModel,
        )
        from src.auth.service import AuthService
        from src.shared.logging import obter_logger_seguranca

        return AuthService(
            usuario_repo=UsuarioRepositorySqlModel(session),
            token_repo=RefreshTokenRepositorySqlModel(session),
            hash_service=self.hash_service(),
            jwt_service=self.jwt_service(),
            access_ttl_minutos=self.settings.access_token_expire_minutes,
            refresh_ttl_dias=self.settings.refresh_token_expire_days,
            logger_seguranca=obter_logger_seguranca(),
        )

    def __repr__(self) -> str:
        return (
            f"Container(registered={list(self._factories)}, "
            f"resolved={list(self._singletons)})"
        )


def construir_container(settings: Settings) -> Container:
    """Constrói o container e registra dependências singleton."""
    from src.auth.security import BcryptHashService, JoseJwtService
    from src.shared.database import criar_engine, criar_session_factory

    c = Container(settings)

    engine = criar_engine(settings.database_url)
    session_factory = criar_session_factory(engine)

    c.register_singleton("Engine", lambda _: engine)
    c.register_singleton("SessionFactory", lambda _: session_factory)
    c.register_singleton(
        "HashService",
        lambda c: BcryptHashService(rounds=c.settings.bcrypt_rounds),
    )
    c.register_singleton(
        "JwtService",
        lambda c: JoseJwtService(
            secret=c.settings.jwt_secret_key,
            algorithm=c.settings.jwt_algorithm,
            access_ttl_minutos=c.settings.access_token_expire_minutes,
        ),
    )

    c.register_singleton("AnthropicClient", _construir_anthropic_client)
    c.register_singleton("SugeridorHistoria", _construir_sugeridor_historia)

    # Pipeline adapters (singletons — todos stateless).
    c.register_singleton("RoteiroGenerator", _construir_roteiro_generator)
    c.register_singleton("TtsProvider", _construir_tts_provider)
    c.register_singleton("Transcription", _construir_transcription)
    c.register_singleton("StockVideo", _construir_stock_video)
    c.register_singleton("VideoComposer", _construir_video_composer)
    c.register_singleton("Storage", _construir_storage)
    c.register_singleton("PipelineOrchestrator", _construir_pipeline_orchestrator)

    return c


def _construir_anthropic_client(c: Container):
    """Cliente Anthropic singleton, ou None se a chave não estiver configurada."""
    if not c.settings.anthropic_api_key:
        return None
    from anthropic import Anthropic
    return Anthropic(api_key=c.settings.anthropic_api_key)


def _construir_sugeridor_historia(c: Container):
    """ClaudeSugeridor singleton, ou None se não há cliente Anthropic disponível."""
    client = c.resolve("AnthropicClient")
    if client is None:
        return None
    from src.temas.providers._claude_sugeridor import ClaudeSugeridor
    return ClaudeSugeridor(client=client, modelo=c.settings.anthropic_modelo_sugeridor)


def _construir_roteiro_generator(c: Container):
    from src.pipeline.adapters.claude_roteiro_generator import ClaudeRoteiroGenerator
    client = c.resolve("AnthropicClient")
    if client is None:
        raise RuntimeError(
            "ANTHROPIC_API_KEY não configurado — necessário para a feature `videos`"
        )
    return ClaudeRoteiroGenerator(
        client=client,
        modelo_roteiro=c.settings.anthropic_modelo_roteiro,
        modelo_cenas=c.settings.anthropic_modelo_cenas,
        modelo_post=c.settings.anthropic_modelo_post,
    )


def _construir_tts_provider(c: Container):
    from src.pipeline.adapters.edge_tts_provider import EdgeTtsProvider
    return EdgeTtsProvider(voz_padrao=c.settings.tts_voice)


def _construir_transcription(c: Container):
    from src.pipeline.adapters.whisper_transcription import WhisperTranscription
    return WhisperTranscription(modelo=c.settings.whisper_model)


def _construir_stock_video(c: Container):
    from src.pipeline.adapters.pexels_stock_video import PexelsStockVideo
    return PexelsStockVideo(api_key=c.settings.pexels_api_key)


def _construir_video_composer(c: Container):  # noqa: ARG001
    from src.pipeline.adapters.ffmpeg_video_composer import FfmpegVideoComposer
    return FfmpegVideoComposer()


def _construir_storage(c: Container):
    from src.pipeline.adapters.filesystem_storage import FilesystemStorage
    return FilesystemStorage(
        raiz=c.settings.storage_dir,
        pasta_musicas=c.settings.pasta_musicas,
    )


def _construir_pipeline_orchestrator(c: Container):
    from src.pipeline import PipelineOrchestrator
    return PipelineOrchestrator(
        roteiro_gen=c.roteiro_generator(),
        tts=c.tts_provider(),
        transcription=c.transcription(),
        stock=c.stock_video(),
        composer=c.video_composer(),
        storage=c.storage(),
    )
