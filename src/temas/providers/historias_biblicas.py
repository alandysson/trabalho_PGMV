"""Provider de Histórias Bíblicas.

Catálogo curado de narrativas conhecidas do AT e NT. System prompt
neutro: sem teologia da prosperidade, sem denominação específica,
respeito ao texto original.
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
    HistoriaEscolhida("davi_e_golias", "Davi e Golias", "1 Samuel 17", ["Davi", "Golias", "Saul"], "coragem"),
    HistoriaEscolhida("daniel_na_cova", "Daniel na Cova dos Leões", "Daniel 6", ["Daniel", "Dario"], "fé"),
    HistoriaEscolhida("jonas_e_o_grande_peixe", "Jonas e o Grande Peixe", "Jonas 1-4", ["Jonas"], "obediência"),
    HistoriaEscolhida("jose_no_egito", "José no Egito", "Gênesis 37-50", ["José", "Faraó", "irmãos de José"], "perdão"),
    HistoriaEscolhida("moises_e_o_mar_vermelho", "Moisés e o Mar Vermelho", "Êxodo 14", ["Moisés", "Faraó"], "libertação"),
    HistoriaEscolhida("noe_e_a_arca", "Noé e a Arca", "Gênesis 6-9", ["Noé"], "obediência"),
    HistoriaEscolhida("ester_rainha", "Ester, a Rainha que Salvou seu Povo", "Ester 1-10", ["Ester", "Mardoqueu", "Hamã"], "coragem"),
    HistoriaEscolhida("rute_e_noemi", "Rute e Noemi", "Rute 1-4", ["Rute", "Noemi", "Boaz"], "lealdade"),
    HistoriaEscolhida("eliseu_e_a_viuva", "Eliseu e a Viúva do Azeite", "2 Reis 4", ["Eliseu", "viúva"], "provisão"),
    HistoriaEscolhida("elias_no_monte_carmelo", "Elias no Monte Carmelo", "1 Reis 18", ["Elias", "profetas de Baal"], "fé"),
    HistoriaEscolhida("sansao_e_dalila", "Sansão e Dalila", "Juízes 13-16", ["Sansão", "Dalila"], "queda e redenção"),
    HistoriaEscolhida("gideao_e_os_300", "Gideão e os 300", "Juízes 6-7", ["Gideão"], "fé"),
    HistoriaEscolhida("abra_o_pai_da_fe", "Abraão, o Pai da Fé", "Gênesis 12-22", ["Abraão", "Sara", "Isaque"], "fé"),
    HistoriaEscolhida("jesus_acalma_a_tempestade", "Jesus Acalma a Tempestade", "Marcos 4:35-41", ["Jesus", "discípulos"], "paz"),
    HistoriaEscolhida("o_bom_samaritano", "O Bom Samaritano", "Lucas 10:25-37", ["samaritano", "ferido"], "compaixão"),
    HistoriaEscolhida("o_filho_prodigo", "O Filho Pródigo", "Lucas 15:11-32", ["pai", "filho pródigo", "irmão"], "perdão"),
    HistoriaEscolhida("pedro_caminha_sobre_as_aguas", "Pedro Caminha Sobre as Águas", "Mateus 14:22-33", ["Jesus", "Pedro"], "fé"),
    HistoriaEscolhida("multiplicacao_dos_paes", "A Multiplicação dos Pães", "João 6:1-14", ["Jesus", "discípulos", "menino"], "provisão"),
    HistoriaEscolhida("zaqueu", "Zaqueu, o Coletor de Impostos", "Lucas 19:1-10", ["Jesus", "Zaqueu"], "transformação"),
    HistoriaEscolhida("paulo_em_damasco", "Paulo a Caminho de Damasco", "Atos 9", ["Saulo / Paulo", "Ananias"], "conversão"),
]


_SYSTEM_PROMPT = """Você é um roteirista cristão experiente, criando
narrações curtas (50-70 segundos) de histórias bíblicas pra vídeos
verticais de redes sociais.

REGRAS DE CONTEÚDO:
- Mantenha-se fiel ao texto bíblico — sem invenções de diálogos não
  registrados, sem mudar fatos centrais.
- Tom contemplativo e reverente, não dramático demais.
- Linguagem acessível em português brasileiro; evite jargão teológico
  acadêmico (perícope, querigma, etc.).
- NÃO pregue teologia da prosperidade.
- NÃO faça apologia denominacional (católica, evangélica, etc.).
- Conclua com uma reflexão breve (1 frase), não com pedido de
  inscrição/seguir.

FORMATO:
- 130-160 palavras totais.
- Comece com um gancho narrativo nos primeiros 5-8 segundos.
- Use frases curtas e ritmo cadenciado (vai virar narração TTS).
"""


class HistoriasBiblicasProvider(BaseTemaProvider):
    def __init__(
        self,
        sugeridor: SugeridorHistoriaProtocol | None = None,
        historias_repo: HistoriaSugeridaRepositoryProtocol | None = None,
    ) -> None:
        self._sugeridor = sugeridor
        self._historias_repo = historias_repo

    @property
    def tema_id(self) -> str:
        return "historias_biblicas"

    @property
    def nome_exibicao(self) -> str:
        return "Histórias com Deus"

    def metadata(self) -> MetadadosTema:
        return MetadadosTema(
            id=self.tema_id,
            nome=self.nome_exibicao,
            descricao="Histórias bíblicas narradas em 1 minuto, com reverência ao texto.",
            icone="📖",
            cor_destaque="#1F3864",
            exemplos=["Davi e Golias", "Daniel na cova", "Jonas e o grande peixe"],
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
            periodo="antiguidade",
            paleta="tons dourados, ocre, areia",
            ambientacao="deserto, vilas antigas, templos, paisagens do oriente médio",
            palavras_chave_extras=["ancient", "biblical", "desert", "old village", "candle"],
        )
