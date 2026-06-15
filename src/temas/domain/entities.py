"""Entidades de domínio do módulo `temas`.

DTOs internos consumidos pelos providers e pelo registry. NÃO confundir
com `schemas.py` (DTOs HTTP).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class HistoriaEscolhida:
    """Uma história selecionada por um `BaseTemaProvider`.

    O `id` é estável (snake_case) — usado pra rastrear histórias recentes
    e evitar repetição. `referencia` é livre: pra Bíblia é "1 Samuel 17",
    pra mitologia "Mitologia Grega", pra fábula "Esopo", etc.
    """

    id: str
    titulo: str
    referencia: str
    personagens: list[str] = field(default_factory=list)
    tema_central: str = ""


@dataclass(frozen=True)
class MetadadosTema:
    """Metadados de exibição de um tema (para a tela de catálogo do app)."""

    id: str
    nome: str
    descricao: str
    icone: str
    cor_destaque: str
    exemplos: list[str]


@dataclass(frozen=True)
class RestricoesVisuais:
    """Hints pra busca de stock no Pexels (a feature `pipeline` vai consumir)."""

    periodo: str = ""
    paleta: str = ""
    ambientacao: str = ""
    palavras_chave_extras: list[str] = field(default_factory=list)
