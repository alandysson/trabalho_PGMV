"""Modelos SQLModel da feature `temas`.

`HistoriaSugerida` é o cache de sugestões dinâmicas geradas pelo
`SugeridorHistoriaProtocol` — cresce ao longo do tempo, sem precisar
de deploy pra expandir o catálogo dos providers.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlmodel import Field, SQLModel


def _agora() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _gerar_id() -> str:
    return f"hs_{uuid4().hex[:12]}"


class HistoriaSugerida(SQLModel, table=True):
    __tablename__ = "historias_sugeridas"

    id: str = Field(default_factory=_gerar_id, primary_key=True)
    tema_id: str = Field(index=True, max_length=64)

    # `historia_id_estavel` é o snake_case sugerido pelo LLM — usado pra
    # rastrear como item de `ids_recentes` em chamadas futuras.
    historia_id_estavel: str = Field(index=True, max_length=128)

    titulo: str = Field(max_length=200)
    referencia: str = Field(default="", max_length=200)
    personagens_json: str = Field(default="[]")  # JSON-encoded list[str]
    tema_central: str = Field(default="", max_length=100)

    criado_em: datetime = Field(default_factory=_agora)
