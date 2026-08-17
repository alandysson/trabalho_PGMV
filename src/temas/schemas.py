"""Schemas Pydantic (DTOs HTTP) da feature `temas`.

Catálogo público — não expõe `system_prompt` nem `restricoes_visuais`,
que são detalhes internos consumidos pela feature `pipeline`.
"""

from __future__ import annotations

from pydantic import BaseModel

from src.temas.domain.entities import MetadadosTema
from src.temas.domain.provider_protocol import BaseTemaProvider


class TemaResponse(BaseModel):
    id: str
    nome: str
    descricao: str
    icone: str
    cor_destaque: str
    exemplos: list[str]

    @classmethod
    def de_metadados(cls, m: MetadadosTema) -> "TemaResponse":
        return cls(
            id=m.id,
            nome=m.nome,
            descricao=m.descricao,
            icone=m.icone,
            cor_destaque=m.cor_destaque,
            exemplos=m.exemplos,
        )

    @classmethod
    def de_provider(cls, p: BaseTemaProvider) -> "TemaResponse":
        return cls.de_metadados(p.metadata())


class ListarTemasResponse(BaseModel):
    temas: list[TemaResponse]
