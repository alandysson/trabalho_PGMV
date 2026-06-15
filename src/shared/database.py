"""Infraestrutura de banco de dados (SQLModel + SQLite).

Ver ADR-0006 para justificativa da escolha de SQLite + SQLModel.

API exposta:
    criar_engine(database_url)       -> Engine
    criar_session_factory(engine)    -> Callable[[], Session]
    criar_tabelas(engine)            -> None
"""

from __future__ import annotations

from typing import Callable

from sqlalchemy import Engine
from sqlmodel import Session, SQLModel, create_engine


def criar_engine(database_url: str) -> Engine:
    """Cria o engine SQLModel.

    Para SQLite, desabilita `check_same_thread` (necessário sob ASGI/uvicorn,
    onde a sessão pode ser usada em threads distintos do que a criou).
    """
    connect_args: dict[str, object] = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    return create_engine(database_url, connect_args=connect_args, echo=False)


def criar_session_factory(engine: Engine) -> Callable[[], Session]:
    def factory() -> Session:
        return Session(engine)

    return factory


def criar_tabelas(engine: Engine) -> None:
    """Cria todas as tabelas declaradas via SQLModel.

    Útil pra bootstrap em desenvolvimento. Em produção, preferir migrations
    (Alembic) — fora do escopo desta sessão.
    """
    SQLModel.metadata.create_all(engine)
