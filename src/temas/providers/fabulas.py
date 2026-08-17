"""Provider de Fábulas (Esopo + La Fontaine).

Tom didático com encerramento explícito em "moral da história".
"""

from __future__ import annotations

from src.temas.data.repository_protocol import HistoriaSugeridaRepositoryProtocol
from src.temas.domain.entities import (
    HistoriaEscolhida,
    MetadadosTema,
    RestricoesVisuais,
)
from src.temas.domain.provider_protocol import BaseTemaProvider
from src.temas.domain.sugeridor_protocol import SugeridorHistoriaProtocol
from src.temas.providers._base import escolher_com_sugeridor


_CATALOGO: list[HistoriaEscolhida] = [
    HistoriaEscolhida("a_raposa_e_as_uvas", "A Raposa e as Uvas", "Esopo", ["raposa"], "racionalização"),
    HistoriaEscolhida("a_lebre_e_a_tartaruga", "A Lebre e a Tartaruga", "Esopo", ["lebre", "tartaruga"], "perseverança"),
    HistoriaEscolhida("a_cigarra_e_a_formiga", "A Cigarra e a Formiga", "La Fontaine", ["cigarra", "formiga"], "trabalho"),
    HistoriaEscolhida("o_lobo_e_o_cordeiro", "O Lobo e o Cordeiro", "Esopo", ["lobo", "cordeiro"], "injustiça"),
    HistoriaEscolhida("o_corvo_e_a_raposa", "O Corvo e a Raposa", "La Fontaine", ["corvo", "raposa"], "vaidade"),
    HistoriaEscolhida("o_leao_e_o_rato", "O Leão e o Rato", "Esopo", ["leão", "rato"], "gratidão"),
    HistoriaEscolhida("o_galo_e_a_perola", "O Galo e a Pérola", "Esopo", ["galo"], "valor relativo"),
    HistoriaEscolhida("a_galinha_dos_ovos_de_ouro", "A Galinha dos Ovos de Ouro", "Esopo", ["camponês", "galinha"], "ganância"),
    HistoriaEscolhida("o_pastor_mentiroso", "O Pastor Mentiroso", "Esopo", ["pastor"], "verdade"),
    HistoriaEscolhida("o_cao_e_o_osso", "O Cão e o Osso no Reflexo", "Esopo", ["cão"], "ambição cega"),
    HistoriaEscolhida("o_vento_e_o_sol", "O Vento e o Sol", "Esopo", ["vento", "sol"], "persuasão"),
    HistoriaEscolhida("o_burro_e_o_cavalo", "O Burro e o Cavalo", "Esopo", ["burro", "cavalo"], "solidariedade"),
    HistoriaEscolhida("a_formiga_e_a_pomba", "A Formiga e a Pomba", "Esopo", ["formiga", "pomba"], "reciprocidade"),
    HistoriaEscolhida("os_dois_amigos_e_o_urso", "Os Dois Amigos e o Urso", "Esopo", ["amigos", "urso"], "amizade verdadeira"),
    HistoriaEscolhida("o_velho_e_a_morte", "O Velho e a Morte", "Esopo", ["velho", "morte"], "ironia da vida"),
]


_SYSTEM_PROMPT = """Você é um contador de fábulas, criando narrações
curtas (50-70 segundos) pra vídeos verticais.

REGRAS DE CONTEÚDO:
- Tom narrativo clássico — "Era uma vez..." ou abertura equivalente é
  bem-vindo.
- Personagens são animais ou figuras simbólicas; respeite a versão
  tradicional (não invente personagens).
- Conclua SEMPRE com a frase "Moral da história:" seguida de uma
  lição curta (1 linha).
- Linguagem simples e visual, como se estivesse contando pra criança
  inteligente.

FORMATO:
- 130-160 palavras totais.
- A moral da história ocupa a última frase, claramente marcada.
- Ritmo cadenciado (vai virar TTS).
"""


class FabulasProvider(BaseTemaProvider):
    def __init__(
        self,
        sugeridor: SugeridorHistoriaProtocol | None = None,
        historias_repo: HistoriaSugeridaRepositoryProtocol | None = None,
    ) -> None:
        self._sugeridor = sugeridor
        self._historias_repo = historias_repo

    @property
    def tema_id(self) -> str:
        return "fabulas"

    @property
    def nome_exibicao(self) -> str:
        return "Fábulas"

    def metadata(self) -> MetadadosTema:
        return MetadadosTema(
            id=self.tema_id,
            nome=self.nome_exibicao,
            descricao="Fábulas clássicas com lições de vida em 1 minuto.",
            icone="🦊",
            cor_destaque="#2E7D32",
            exemplos=["A raposa e as uvas", "A lebre e a tartaruga", "O lobo e o cordeiro"],
        )

    def escolher_historia(self, ids_recentes: list[str]) -> HistoriaEscolhida:
        return escolher_com_sugeridor(
            tema_id=self.tema_id,
            tema_nome=self.nome_exibicao,
            catalogo_curado=_CATALOGO,
            ids_recentes=ids_recentes,
            sugeridor=self._sugeridor,
            historias_repo=self._historias_repo,
        )

    def system_prompt_roteiro(self) -> str:
        return _SYSTEM_PROMPT

    def restricoes_visuais(self) -> RestricoesVisuais:
        return RestricoesVisuais(
            periodo="atemporal",
            paleta="tons naturais, verdes, terrosos",
            ambientacao="floresta, campo, animais em close, sol entre folhas",
            palavras_chave_extras=["forest", "animal close up", "wildlife", "meadow", "nature"],
        )
