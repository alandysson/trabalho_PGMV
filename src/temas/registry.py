"""Registry de provedores de tema.

Antes era um dict module-level; agora é uma função construtora porque
cada provider precisa receber dependências injetadas (`sugeridor` +
`historias_repo`). O container chama `construir_registry(...)` por
request.

Adicionar tema novo continua sendo barato: importa a classe + registra
uma linha aqui. Zero modificação nos providers existentes (ADR-0008).
"""

from __future__ import annotations

from typing import Mapping

from src.temas.data.repository_protocol import HistoriaSugeridaRepositoryProtocol
from src.temas.domain.exceptions import TemaNaoEncontrado
from src.temas.domain.provider_protocol import BaseTemaProvider
from src.temas.domain.sugeridor_protocol import SugeridorHistoriaProtocol
from src.temas.providers.curiosidades import CuriosidadesProvider
from src.temas.providers.fabulas import FabulasProvider
from src.temas.providers.historias_biblicas import HistoriasBiblicasProvider
from src.temas.providers.mitologia import MitologiaProvider


_CLASSES_DOS_PROVIDERS = [
    HistoriasBiblicasProvider,
    MitologiaProvider,
    CuriosidadesProvider,
    FabulasProvider,
]


class Registry:
    def __init__(self, providers: Mapping[str, BaseTemaProvider]) -> None:
        self._providers: dict[str, BaseTemaProvider] = dict(providers)

    def obter(self, tema_id: str) -> BaseTemaProvider:
        p = self._providers.get(tema_id)
        if p is None:
            raise TemaNaoEncontrado(tema_id=tema_id)
        return p

    def listar(self) -> list[BaseTemaProvider]:
        return list(self._providers.values())

    def ids(self) -> list[str]:
        return list(self._providers.keys())


def construir_registry(
    sugeridor: SugeridorHistoriaProtocol | None = None,
    historias_repo: HistoriaSugeridaRepositoryProtocol | None = None,
) -> Registry:
    """Instancia todos os providers conhecidos com as dependências passadas.

    Quando `sugeridor` é None, cai no catálogo estático puro (o pool
    nunca é reabastecido por LLM). Útil pra testes e pra rotas
    públicas que não precisam do Anthropic.
    """
    providers: dict[str, BaseTemaProvider] = {}
    for cls in _CLASSES_DOS_PROVIDERS:
        instancia = cls(sugeridor=sugeridor, historias_repo=historias_repo)
        providers[instancia.tema_id] = instancia
    return Registry(providers)


# Conveniência: registry estático sem injeção, pra uso direto em código
# que só precisa de catálogo curado (ex.: listagem em GET /temas).
_registry_estatico: Registry | None = None


def registry_estatico() -> Registry:
    global _registry_estatico
    if _registry_estatico is None:
        _registry_estatico = construir_registry(sugeridor=None, historias_repo=None)
    return _registry_estatico


# ----- Atalhos retrocompat (consumidos por routes.py e __init__.py) -----

def obter_tema(tema_id: str) -> BaseTemaProvider:
    return registry_estatico().obter(tema_id)


def listar_temas() -> list[BaseTemaProvider]:
    return registry_estatico().listar()


def ids_disponiveis() -> list[str]:
    return registry_estatico().ids()
