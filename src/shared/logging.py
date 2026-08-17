"""Configuração de logging do backend.

Setup simples (stdlib `logging` com formato estruturado). Pode evoluir pra
JSON logger / structlog quando observabilidade externa entrar em cena.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_FORMATO = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATA_FORMATO = "%Y-%m-%d %H:%M:%S"

_FORMATO_SEGURANCA = "%(asctime)s | %(message)s"
_LOGGER_SEGURANCA = "seguranca"
_ARQUIVO_SEGURANCA = Path("logs/seguranca.log")


def configurar_logging(level: str = "INFO") -> None:
    """Configura o handler raiz uma única vez (idempotente em re-chamada)."""
    nivel_numerico = logging.getLevelName(level.upper())
    if not isinstance(nivel_numerico, int):
        nivel_numerico = logging.INFO

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(logging.Formatter(fmt=_FORMATO, datefmt=_DATA_FORMATO))

    raiz = logging.getLogger()
    raiz.setLevel(nivel_numerico)

    raiz.handlers.clear()
    raiz.addHandler(handler)

    logging.getLogger("uvicorn.access").setLevel(nivel_numerico)


def obter_logger(nome: str) -> logging.Logger:
    return logging.getLogger(nome)


def obter_logger_seguranca() -> logging.Logger:
    """Logger dedicado para eventos de auth — arquivo separado, sem propagar.

    Eventos esperados: registro, login_sucesso, login_falha, refresh_sucesso,
    refresh_reuso_invasao, logout, logout_tudo, troca_senha. NUNCA inclui
    senhas ou tokens (nem hash).
    """
    log = logging.getLogger(_LOGGER_SEGURANCA)
    if getattr(log, "_inicializado", False):
        return log

    _ARQUIVO_SEGURANCA.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(_ARQUIVO_SEGURANCA, encoding="utf-8")
    handler.setFormatter(logging.Formatter(fmt=_FORMATO_SEGURANCA, datefmt=_DATA_FORMATO))

    log.setLevel(logging.INFO)
    log.addHandler(handler)
    log.propagate = False
    log._inicializado = True  # type: ignore[attr-defined]
    return log
