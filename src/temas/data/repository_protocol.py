"""Interface do repositório de sugestões cacheadas."""

from __future__ import annotations

from typing import Protocol

from src.temas.domain.entities import HistoriaEscolhida


class HistoriaSugeridaRepositoryProtocol(Protocol):
    def salvar(self, tema_id: str, historia: HistoriaEscolhida) -> None: ...

    def listar_por_tema(self, tema_id: str) -> list[HistoriaEscolhida]: ...
