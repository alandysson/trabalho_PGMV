"""Helpers compartilhados pelos providers concretos.

A lógica de escolha vive aqui pra evitar duplicação. Cada provider
concreto declara apenas:
- catálogo curado (lista de `HistoriaEscolhida`)
- nome de exibição (pro contexto enviado ao sugeridor)
- system prompt, restrições visuais e metadata
"""

from __future__ import annotations

import logging
import secrets

from src.temas.data.repository_protocol import HistoriaSugeridaRepositoryProtocol
from src.temas.domain.entities import HistoriaEscolhida
from src.temas.domain.exceptions import CatalogoVazio
from src.temas.domain.sugeridor_protocol import (
    ContextoSugestao,
    FalhaSugestao,
    SugeridorHistoriaProtocol,
)


_log = logging.getLogger(__name__)


def escolher_com_sugeridor(
    *,
    tema_id: str,
    tema_nome: str,
    catalogo_curado: list[HistoriaEscolhida],
    ids_recentes: list[str],
    sugeridor: SugeridorHistoriaProtocol | None,
    historias_repo: HistoriaSugeridaRepositoryProtocol | None,
) -> HistoriaEscolhida:
    """Escolhe uma história aplicando catálogo curado + cache + sugeridor.

    Fluxo:
    1. Pool = catálogo curado ∪ cache (do `historias_repo`, se existir).
    2. Pool filtrado por `ids_recentes` ≠ ∅ → sorteia daí (sem custo).
    3. Pool filtrado = ∅ e há `sugeridor` → pede nova sugestão. Cacheia.
    4. Fallback: sorteia do pool inteiro ignorando recentes (nunca quebra).
    """
    if not catalogo_curado:
        raise CatalogoVazio(tema_id=tema_id)

    pool = list(catalogo_curado)
    if historias_repo is not None:
        pool.extend(historias_repo.listar_por_tema(tema_id))

    recentes = set(ids_recentes or [])
    candidatos = [h for h in pool if h.id not in recentes]

    if candidatos:
        return candidatos[secrets.randbelow(len(candidatos))]

    if sugeridor is not None:
        try:
            sugerida = sugeridor.sugerir(
                ContextoSugestao(
                    tema_id=tema_id,
                    tema_nome=tema_nome,
                    exemplos_existentes=[h.titulo for h in catalogo_curado[:10]],
                    ids_a_evitar=[h.id for h in pool],
                )
            )
            if historias_repo is not None:
                historias_repo.salvar(tema_id, sugerida)
            return sugerida
        except FalhaSugestao as exc:
            _log.info("Sugeridor falhou pra tema=%s — fallback. %s", tema_id, exc)

    # Fallback: sorteia do pool ignorando recentes (melhor repetir que falhar).
    return pool[secrets.randbelow(len(pool))]
