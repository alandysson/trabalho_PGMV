"""Interface abstrata para provedores de tema.

Cada tema é um plugin que implementa esta classe. Adicionar um tema novo
= criar `src/temas/providers/<novo>.py` com uma classe que herda de
`BaseTemaProvider`, e registrá-lo no `src/temas/registry.py`. **Zero
modificação em código existente** — OCP cumprido (ver ADR-0008).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.temas.domain.entities import HistoriaEscolhida, MetadadosTema, RestricoesVisuais


class BaseTemaProvider(ABC):
    """Contrato comum a todos os provedores de tema."""

    @property
    @abstractmethod
    def tema_id(self) -> str:
        """Identificador estável em snake_case. Ex.: 'historias_biblicas'."""

    @property
    @abstractmethod
    def nome_exibicao(self) -> str:
        """Nome amigável pra UI. Ex.: 'Histórias com Deus'."""

    @abstractmethod
    def metadata(self) -> MetadadosTema:
        """Metadados de exibição (icone, cor, descrição, exemplos)."""

    @abstractmethod
    def escolher_historia(self, ids_recentes: list[str]) -> HistoriaEscolhida:
        """Escolhe uma história deste tema evitando IDs em `ids_recentes`.

        Deve levantar `CatalogoVazio` se o filtro deixar a lista vazia
        (situação rara: usuário gerou todos os itens do tema).
        """

    @abstractmethod
    def system_prompt_roteiro(self) -> str:
        """System prompt que guia o Claude a gerar o roteiro neste tema.

        Define tom, restrições de conteúdo, formato esperado. NÃO inclui
        a história específica — isso vem no user message.
        """

    @abstractmethod
    def restricoes_visuais(self) -> RestricoesVisuais:
        """Hints pra busca de stock no Pexels (período, paleta, ambientação)."""
