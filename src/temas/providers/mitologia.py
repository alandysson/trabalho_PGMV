"""Provider de Mitologia (grega, nórdica, egípcia).

Tom épico e respeitoso com a cultura original — sem julgamento moderno
das crenças antigas, sem trivialização cinematográfica.
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
    # Mitologia grega
    HistoriaEscolhida("prometeu_rouba_o_fogo", "Prometeu Rouba o Fogo dos Deuses", "Mitologia Grega", ["Prometeu", "Zeus"], "rebeldia"),
    HistoriaEscolhida("pandora_e_a_caixa", "Pandora e a Caixa", "Mitologia Grega", ["Pandora", "Epimeteu"], "curiosidade"),
    HistoriaEscolhida("hercules_e_os_12_trabalhos", "Hércules e os 12 Trabalhos", "Mitologia Grega", ["Hércules", "Hera"], "redenção"),
    HistoriaEscolhida("perseu_e_medusa", "Perseu e Medusa", "Mitologia Grega", ["Perseu", "Medusa", "Atena"], "coragem"),
    HistoriaEscolhida("odisseu_e_o_cavalo_de_troia", "Odisseu e o Cavalo de Tróia", "Mitologia Grega", ["Odisseu", "Helena"], "astúcia"),
    HistoriaEscolhida("edipo_rei", "A Tragédia de Édipo Rei", "Mitologia Grega", ["Édipo", "Jocasta"], "destino"),
    HistoriaEscolhida("aracne_e_atena", "Aracne, a Tecelã que Desafiou Atena", "Mitologia Grega", ["Aracne", "Atena"], "orgulho"),
    HistoriaEscolhida("sisifo_e_a_pedra", "Sísifo e a Pedra Eterna", "Mitologia Grega", ["Sísifo"], "absurdo"),
    HistoriaEscolhida("midas_e_o_toque_de_ouro", "O Rei Midas e o Toque de Ouro", "Mitologia Grega", ["Midas", "Dionísio"], "ganância"),
    HistoriaEscolhida("orfeu_e_euridice", "Orfeu e Eurídice", "Mitologia Grega", ["Orfeu", "Eurídice", "Hades"], "amor e perda"),
    HistoriaEscolhida("teseu_e_o_minotauro", "Teseu e o Minotauro", "Mitologia Grega", ["Teseu", "Ariadne", "Minotauro"], "coragem"),
    HistoriaEscolhida("icaro_voa_alto_demais", "Ícaro Voa Alto Demais", "Mitologia Grega", ["Ícaro", "Dédalo"], "arrogância"),
    # Mitologia nórdica
    HistoriaEscolhida("thor_e_o_martelo_mjolnir", "Thor e o Martelo Mjölnir", "Mitologia Nórdica", ["Thor", "Loki"], "honra"),
    HistoriaEscolhida("loki_e_a_morte_de_balder", "Loki e a Morte de Balder", "Mitologia Nórdica", ["Loki", "Balder", "Hodur"], "traição"),
    HistoriaEscolhida("odin_e_a_sabedoria", "Odin Sacrifica um Olho pela Sabedoria", "Mitologia Nórdica", ["Odin", "Mimir"], "sacrifício"),
    HistoriaEscolhida("ragnarok_o_crepusculo_dos_deuses", "Ragnarök, o Crepúsculo dos Deuses", "Mitologia Nórdica", ["Odin", "Thor", "Loki", "Fenrir"], "fim e recomeço"),
    HistoriaEscolhida("yggdrasil_a_arvore_do_mundo", "Yggdrasil, a Árvore do Mundo", "Mitologia Nórdica", [], "cosmologia"),
    # Mitologia egípcia
    HistoriaEscolhida("isis_e_osiris", "Ísis e Osíris: Amor que Vence a Morte", "Mitologia Egípcia", ["Ísis", "Osíris", "Set"], "amor"),
    HistoriaEscolhida("anubis_pesa_o_coracao", "Anúbis Pesa o Coração", "Mitologia Egípcia", ["Anúbis", "Maat"], "julgamento"),
    HistoriaEscolhida("ra_e_a_jornada_solar", "Rá e a Jornada Solar", "Mitologia Egípcia", ["Rá", "Apófis"], "renovação"),
]


_SYSTEM_PROMPT = """Você é um narrador especializado em mitologia
antiga, criando relatos curtos (50-70 segundos) pra vídeos verticais.

REGRAS DE CONTEÚDO:
- Tom épico, mas sem exageros teatrais. Lembre que é mito ANTIGO —
  trate com gravidade, não com brincadeira.
- Respeite a cultura original. Sem julgamento moderno do tipo "que
  bobagem acreditar nisso".
- Quando o mito for grego, use nomes gregos (Zeus, não Júpiter; Atena,
  não Minerva).
- Sem misturar Marvel/Hollywood: Thor aqui é o deus nórdico, não o
  super-herói loiro.
- Conclua com uma reflexão breve sobre o que o mito revela do humano.

FORMATO:
- 130-160 palavras.
- Gancho narrativo nos primeiros 5-8 segundos.
- Frases curtas, cadenciadas (vai virar TTS).
"""


class MitologiaProvider(BaseTemaProvider):
    def __init__(
        self,
        sugeridor: SugeridorHistoriaProtocol | None = None,
        historias_repo: HistoriaSugeridaRepositoryProtocol | None = None,
    ) -> None:
        self._sugeridor = sugeridor
        self._historias_repo = historias_repo

    @property
    def tema_id(self) -> str:
        return "mitologia"

    @property
    def nome_exibicao(self) -> str:
        return "Mitos Antigos"

    def metadata(self) -> MetadadosTema:
        return MetadadosTema(
            id=self.tema_id,
            nome=self.nome_exibicao,
            descricao="Mitologia grega, nórdica e egípcia, narrada em 1 minuto.",
            icone="⚡",
            cor_destaque="#8B0000",
            exemplos=["Prometeu rouba o fogo", "Thor e Loki", "Ísis e Osíris"],
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
            paleta="paleta dramática, sombras profundas, dourado",
            ambientacao="montanhas, mares revoltos, templos em ruínas, fogo, nevoeiro",
            palavras_chave_extras=["ancient temple", "stormy sea", "mountain peak", "fire", "warrior"],
        )
