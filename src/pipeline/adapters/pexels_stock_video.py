"""Adapter para Pexels Videos API.

Delega ao `legacy/pexels.py`. Lê `PEXELS_API_KEY` do env — setamos a
partir das Settings no construtor pra manter o legacy sem mudanças.
"""

from __future__ import annotations

import os
from pathlib import Path

from legacy.pexels import buscar_e_baixar_cenas as _buscar_e_baixar
from src.pipeline.domain.entities import Cena, CenaComStock


class PexelsStockVideo:
    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("PEXELS_API_KEY não configurada")
        os.environ["PEXELS_API_KEY"] = api_key

    def buscar_e_baixar(
        self,
        *,
        cenas: list[Cena],
        pasta_saida: Path,
    ) -> list[CenaComStock]:
        # O legacy espera dicts; convertendo.
        dicts_cenas = [
            {
                "ordem": c.ordem,
                "trecho_texto": c.trecho_texto,
                "query_pexels": c.query_pexels,
                "descricao_visual": c.descricao_visual,
            }
            for c in cenas
        ]
        enriquecidas = _buscar_e_baixar(dicts_cenas, pasta_saida)

        resultado: list[CenaComStock] = []
        for original, enriq in zip(cenas, enriquecidas):
            caminho = enriq.get("caminho_arquivo")
            resultado.append(
                CenaComStock(
                    cena=original,
                    caminho_arquivo=Path(caminho) if caminho else None,
                    pexels_id=enriq.get("pexels_id"),
                    pexels_url=enriq.get("pexels_url", ""),
                    fotografo_nome=enriq.get("fotografo_nome", ""),
                    fotografo_url=enriq.get("fotografo_url", ""),
                )
            )
        return resultado
