"""Configurações da aplicação (Pydantic Settings).

Lê variáveis do `.env` na raiz do projeto. Campos específicos de features
(ex.: JWT, BCRYPT) entram aqui à medida que cada feature for implementada —
mantendo este módulo enxuto e refletindo apenas o que já existe em código.
"""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Vídeos Narrados API"
    app_version: str = "1.0.0"
    environment: str = Field(default="development", description="development | staging | production")

    database_url: str = Field(
        default="sqlite:///./videos.db",
        description="URL do banco. Default SQLite local; ver ADR-0006.",
    )

    log_level: str = Field(default="INFO", description="DEBUG | INFO | WARNING | ERROR | CRITICAL")

    cors_origins: list[str] = Field(
        default_factory=list,
        description="Origens permitidas via CORS (JSON array). Em produção, listar explicitamente.",
    )

    cors_origin_regex: str = Field(
        default="",
        description=(
            "Regex de origens permitidas (complementa `cors_origins`). "
            "Útil pra Expo dev: ^exp://.* casa qualquer URL `exp://...`."
        ),
    )

    storage_dir: Path = Field(
        default=Path("storage"),
        description="Diretório raiz para arquivos gerados (vídeos, áudios, transcrições).",
    )

    # ----- Auth (feature `auth`) -----
    # JWT_SECRET_KEY é required: gere com
    #   python -c "import secrets; print(secrets.token_urlsafe(64))"
    jwt_secret_key: str = Field(description="Chave HMAC para assinar JWT (não commitar).")
    jwt_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=15, ge=1)
    refresh_token_expire_days: int = Field(default=30, ge=1)
    bcrypt_rounds: int = Field(default=12, ge=4, le=15)
    rate_limit_login_tentativas: int = Field(default=5, ge=1)
    rate_limit_login_janela_minutos: int = Field(default=15, ge=1)

    # ----- Temas / Anthropic -----
    # ANTHROPIC_API_KEY pode ficar vazio em dev — o ClaudeSugeridor só é
    # chamado quando o catálogo curado se esgota; sem chave, providers
    # caem no fallback estático.
    anthropic_api_key: str = Field(default="")
    anthropic_modelo_sugeridor: str = Field(default="claude-haiku-4-5-20251001")
    anthropic_modelo_roteiro: str = Field(default="claude-sonnet-4-6")
    anthropic_modelo_cenas: str = Field(default="claude-haiku-4-5-20251001")
    anthropic_modelo_post: str = Field(default="claude-haiku-4-5-20251001")

    # ----- Pipeline de geração (videos) -----
    pexels_api_key: str = Field(default="")
    tts_voice: str = Field(default="pt-BR-AntonioNeural")
    whisper_model: str = Field(default="base")
    video_duracao_alvo: int = Field(default=60, ge=15, le=180)
    max_jobs_paralelos: int = Field(default=2, ge=1, le=10)
    pasta_musicas: Path = Field(default=Path("assets/music"))
