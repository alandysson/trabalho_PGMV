"""Interface de sugestão dinâmica de histórias.

Quando o catálogo curado de um provider se esgota (filtro de
`ids_recentes` zera o pool), o provider consulta um
`SugeridorHistoriaProtocol` pra propor uma história nova fora da lista.

A implementação concreta vive em `temas/providers/_claude_sugeridor.py`
(prefixo `_` indica detalhe interno — não exportado em `__init__.py`).
Trocar Claude por outro LLM = nova implementação, zero mudança nos
providers.
"""

from __future__ import annotations

from typing import Protocol

from src.temas.domain.entities import HistoriaEscolhida


class ContextoSugestao:
    """Bag de contexto repassado ao sugeridor.

    Não usar Pydantic — instâncias internas, leves; mantém o módulo
    livre de dependência adicional.
    """

    __slots__ = ("tema_id", "tema_nome", "exemplos_existentes", "ids_a_evitar")

    def __init__(
        self,
        tema_id: str,
        tema_nome: str,
        exemplos_existentes: list[str],
        ids_a_evitar: list[str],
    ) -> None:
        self.tema_id = tema_id
        self.tema_nome = tema_nome
        self.exemplos_existentes = exemplos_existentes
        self.ids_a_evitar = ids_a_evitar


class SugeridorHistoriaProtocol(Protocol):
    def sugerir(self, contexto: ContextoSugestao) -> HistoriaEscolhida: ...


class FalhaSugestao(Exception):
    """Sugeridor não conseguiu propor uma história (rede, API, parsing).

    O provider trata como sinal pra cair no fallback (sortear do pool
    ignorando recentes). Nunca propaga 5xx pro cliente.
    """
