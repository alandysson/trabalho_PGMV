"""Provider de Curiosidades históricas e científicas.

Tom didático com fato surpreendente nos primeiros segundos. Foco em
"você sabia?" — gatilhos de curiosidade rápidos.
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
    HistoriaEscolhida("por_que_o_ceu_e_azul", "Por que o Céu é Azul", "Ciência", [], "óptica"),
    HistoriaEscolhida("origem_do_cafe", "A Origem Inesperada do Café", "História", [], "alimento"),
    HistoriaEscolhida("quem_foi_cleopatra", "Quem Foi Cleópatra de Verdade", "Egito Antigo", ["Cleópatra"], "biografia"),
    HistoriaEscolhida("por_que_passamos_a_lavar_as_maos", "Por que Passamos a Lavar as Mãos", "Medicina", ["Semmelweis"], "ciência rejeitada"),
    HistoriaEscolhida("o_homem_que_inventou_o_zero", "O Homem que Inventou o Zero", "Matemática", ["Brahmagupta"], "matemática"),
    HistoriaEscolhida("a_grande_muralha_da_china", "A Grande Muralha Que Não Se Vê do Espaço", "História", [], "mito desfeito"),
    HistoriaEscolhida("por_que_temos_polegares", "Por que Temos Polegares Opostos", "Biologia", [], "evolução"),
    HistoriaEscolhida("a_grande_emergencia_do_y2k", "O Bug do Milênio Que Quase Aconteceu", "Tecnologia", [], "tecnologia"),
    HistoriaEscolhida("origem_dos_emojis", "A Origem Japonesa dos Emojis", "Cultura", ["Shigetaka Kurita"], "comunicação"),
    HistoriaEscolhida("polvos_tem_tres_coracoes", "Polvos Têm Três Corações", "Biologia", [], "vida marinha"),
    HistoriaEscolhida("a_carta_que_demorou_100_anos", "A Carta de Amor Que Demorou 100 Anos", "História", [], "tempo"),
    HistoriaEscolhida("por_que_bocejamos", "Por que Bocejamos (E Por que é Contagioso)", "Neurociência", [], "comportamento"),
    HistoriaEscolhida("a_unica_foto_de_chopin", "A Única Foto Existente de Chopin", "Música", ["Chopin"], "arte"),
    HistoriaEscolhida("o_pi_nunca_termina", "Por que o Número Pi Nunca Termina", "Matemática", [], "infinito"),
    HistoriaEscolhida("o_cao_que_levava_correspondencia", "Owney, o Cão que Levava Correspondência", "História", ["Owney"], "lealdade"),
    HistoriaEscolhida("origem_do_pijama", "A Origem Indiana do Pijama", "Cultura", [], "moda"),
    HistoriaEscolhida("a_arvore_mais_antiga_do_mundo", "A Árvore Mais Antiga do Mundo", "Biologia", [], "natureza"),
    HistoriaEscolhida("o_dia_que_o_mar_secou", "O Dia que o Mar Mediterrâneo Secou", "Geologia", [], "tempo profundo"),
    HistoriaEscolhida("por_que_temos_5_dedos", "Por que Temos Exatamente 5 Dedos", "Evolução", [], "evolução"),
    HistoriaEscolhida("o_acidente_que_criou_o_post_it", "O Acidente Que Criou o Post-it", "Invenções", ["Spencer Silver"], "serendipidade"),
]


_SYSTEM_PROMPT = """Você é um divulgador de ciência e história,
criando "Você Sabia?" curtos (50-70 segundos) pra vídeos verticais.

REGRAS DE CONTEÚDO:
- COMECE com o fato surpreendente nos primeiros 3 segundos. Não enrole
  com introdução genérica do tipo "Hoje eu vou contar...".
- Use uma analogia ou comparação concreta sempre que possível.
- Cite fontes em alto nível ("estudos da NASA", "pesquisadores da USP")
  sem nomear papers — é vídeo curto.
- Sem teoria da conspiração ou fato duvidoso. Tudo deve ser
  consensualmente aceito.
- Tom curioso, animado mas não infantilizado.
- Conclua com pergunta retórica ou conexão prática.

FORMATO:
- 130-160 palavras.
- Frases curtas, ritmo rápido (vai virar TTS).
- Sem listas numeradas — é narração contínua.
"""


class CuriosidadesProvider(BaseTemaProvider):
    def __init__(
        self,
        sugeridor: SugeridorHistoriaProtocol | None = None,
        historias_repo: HistoriaSugeridaRepositoryProtocol | None = None,
    ) -> None:
        self._sugeridor = sugeridor
        self._historias_repo = historias_repo

    @property
    def tema_id(self) -> str:
        return "curiosidades"

    @property
    def nome_exibicao(self) -> str:
        return "Você Sabia?"

    def metadata(self) -> MetadadosTema:
        return MetadadosTema(
            id=self.tema_id,
            nome=self.nome_exibicao,
            descricao="Curiosidades históricas e científicas em 1 minuto.",
            icone="💡",
            cor_destaque="#D4A843",
            exemplos=["Por que o céu é azul", "Origem do café", "Quem foi Cleópatra"],
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
            periodo="contemporâneo",
            paleta="cores vibrantes, brancos limpos, contraste alto",
            ambientacao="laboratórios, cidades modernas, microscópios, mapas, livros",
            palavras_chave_extras=["science", "macro", "laboratory", "city", "modern"],
        )
