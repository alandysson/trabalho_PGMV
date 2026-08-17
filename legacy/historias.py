"""
Módulo de histórias bíblicas.

Mantém uma lista de referência de aproximadamente 50 histórias populares
(Antigo e Novo Testamento) e expõe a função `escolher_historia`, que delega
ao Claude Haiku a escolha de qual história contar — respeitando uma lista
opcional de IDs já contadas recentemente, para evitar repetição.
"""

from __future__ import annotations

import json
import os
from typing import Optional

from anthropic import Anthropic


# Modelo barato para uma decisão simples de seleção.
MODELO_ESCOLHA = "claude-haiku-4-5"


# =========================================================================
# Lista de referência de histórias bíblicas.
# Cada item: id (slug único), titulo, referencia, personagens_principais, tema.
# Fácil de expandir — basta acrescentar novos dicts mantendo o mesmo formato.
# =========================================================================
HISTORIAS_REFERENCIA: list[dict] = [
    # ---------------- Antigo Testamento ----------------
    {
        "id": "criacao",
        "titulo": "A Criação do Mundo",
        "referencia": "Gênesis 1-2",
        "personagens_principais": ["Deus", "Adão", "Eva"],
        "tema": "Origem, propósito da humanidade",
    },
    {
        "id": "ada_eva_queda",
        "titulo": "A Queda de Adão e Eva",
        "referencia": "Gênesis 3",
        "personagens_principais": ["Adão", "Eva", "Serpente"],
        "tema": "Tentação, escolha, consequências",
    },
    {
        "id": "caim_abel",
        "titulo": "Caim e Abel",
        "referencia": "Gênesis 4",
        "personagens_principais": ["Caim", "Abel"],
        "tema": "Inveja, ira, responsabilidade fraterna",
    },
    {
        "id": "noe_arca",
        "titulo": "Noé e a Arca",
        "referencia": "Gênesis 6-9",
        "personagens_principais": ["Noé"],
        "tema": "Obediência, fé contra zombaria, novo começo",
    },
    {
        "id": "torre_babel",
        "titulo": "A Torre de Babel",
        "referencia": "Gênesis 11",
        "personagens_principais": ["Humanidade pós-dilúvio"],
        "tema": "Orgulho, unidade desviada, humildade",
    },
    {
        "id": "abraao_chamado",
        "titulo": "O Chamado de Abraão",
        "referencia": "Gênesis 12",
        "personagens_principais": ["Abraão", "Sara"],
        "tema": "Fé que parte para o desconhecido",
    },
    {
        "id": "sacrificio_isaque",
        "titulo": "O Sacrifício de Isaque",
        "referencia": "Gênesis 22",
        "personagens_principais": ["Abraão", "Isaque"],
        "tema": "Confiança radical, provisão divina",
    },
    {
        "id": "jaco_esau",
        "titulo": "Jacó e Esaú",
        "referencia": "Gênesis 25-33",
        "personagens_principais": ["Jacó", "Esaú", "Isaque"],
        "tema": "Trapaça, reconciliação, transformação",
    },
    {
        "id": "jose_egito",
        "titulo": "José no Egito",
        "referencia": "Gênesis 37-50",
        "personagens_principais": ["José", "Irmãos de José", "Faraó"],
        "tema": "Sonhos, traição, perdão, providência",
    },
    {
        "id": "moises_sarca",
        "titulo": "Moisés e a Sarça Ardente",
        "referencia": "Êxodo 3",
        "personagens_principais": ["Moisés"],
        "tema": "Chamado, presença santa, identidade",
    },
    {
        "id": "moises_pragas",
        "titulo": "As Dez Pragas do Egito",
        "referencia": "Êxodo 7-12",
        "personagens_principais": ["Moisés", "Faraó", "Arão"],
        "tema": "Poder de Deus, libertação, dureza de coração",
    },
    {
        "id": "moises_mar_vermelho",
        "titulo": "Moisés e o Mar Vermelho",
        "referencia": "Êxodo 14",
        "personagens_principais": ["Moisés", "Povo de Israel"],
        "tema": "Livramento impossível, fé no extremo",
    },
    {
        "id": "dez_mandamentos",
        "titulo": "Os Dez Mandamentos",
        "referencia": "Êxodo 20",
        "personagens_principais": ["Moisés"],
        "tema": "Lei, aliança, vida em comunidade",
    },
    {
        "id": "bezerro_ouro",
        "titulo": "O Bezerro de Ouro",
        "referencia": "Êxodo 32",
        "personagens_principais": ["Moisés", "Arão", "Povo de Israel"],
        "tema": "Idolatria, impaciência, intercessão",
    },
    {
        "id": "josue_jerico",
        "titulo": "Josué e os Muros de Jericó",
        "referencia": "Josué 6",
        "personagens_principais": ["Josué"],
        "tema": "Obediência estranha, vitória de Deus",
    },
    {
        "id": "gideao",
        "titulo": "Gideão e os Trezentos",
        "referencia": "Juízes 6-7",
        "personagens_principais": ["Gideão"],
        "tema": "Insegurança vencida, força nos poucos",
    },
    {
        "id": "sansao",
        "titulo": "Sansão e Dalila",
        "referencia": "Juízes 13-16",
        "personagens_principais": ["Sansão", "Dalila"],
        "tema": "Dom desperdiçado, redenção final",
    },
    {
        "id": "rute",
        "titulo": "Rute e Boaz",
        "referencia": "Livro de Rute",
        "personagens_principais": ["Rute", "Noemi", "Boaz"],
        "tema": "Lealdade, providência silenciosa, restauração",
    },
    {
        "id": "samuel_chamado",
        "titulo": "O Chamado do Menino Samuel",
        "referencia": "1 Samuel 3",
        "personagens_principais": ["Samuel", "Eli"],
        "tema": "Ouvir a voz de Deus desde cedo",
    },
    {
        "id": "davi_golias",
        "titulo": "Davi e Golias",
        "referencia": "1 Samuel 17",
        "personagens_principais": ["Davi", "Golias"],
        "tema": "Coragem, fé contra gigantes",
    },
    {
        "id": "davi_saul",
        "titulo": "Davi Poupa Saul",
        "referencia": "1 Samuel 24",
        "personagens_principais": ["Davi", "Saul"],
        "tema": "Domínio próprio, respeito à autoridade",
    },
    {
        "id": "salomao_sabedoria",
        "titulo": "A Sabedoria de Salomão",
        "referencia": "1 Reis 3",
        "personagens_principais": ["Salomão"],
        "tema": "Pedir o que realmente importa",
    },
    {
        "id": "elias_carmelo",
        "titulo": "Elias no Monte Carmelo",
        "referencia": "1 Reis 18",
        "personagens_principais": ["Elias"],
        "tema": "Confronto com a idolatria, fogo de Deus",
    },
    {
        "id": "elias_horebe",
        "titulo": "Elias e o Som Suave no Horebe",
        "referencia": "1 Reis 19",
        "personagens_principais": ["Elias"],
        "tema": "Exaustão, depressão, cuidado de Deus",
    },
    {
        "id": "eliseu_naama",
        "titulo": "Eliseu Cura Naamã",
        "referencia": "2 Reis 5",
        "personagens_principais": ["Eliseu", "Naamã"],
        "tema": "Humildade, obediência simples",
    },
    {
        "id": "ester",
        "titulo": "Ester Salva Seu Povo",
        "referencia": "Livro de Ester",
        "personagens_principais": ["Ester", "Mardoqueu", "Hamã"],
        "tema": "Coragem em hora crítica, propósito",
    },
    {
        "id": "jo",
        "titulo": "A Fé de Jó",
        "referencia": "Livro de Jó",
        "personagens_principais": ["Jó"],
        "tema": "Sofrimento, integridade, restauração",
    },
    {
        "id": "daniel_leoes",
        "titulo": "Daniel na Cova dos Leões",
        "referencia": "Daniel 6",
        "personagens_principais": ["Daniel", "Dario"],
        "tema": "Oração sem medo, livramento",
    },
    {
        "id": "tres_jovens_fornalha",
        "titulo": "Os Três Jovens na Fornalha",
        "referencia": "Daniel 3",
        "personagens_principais": ["Sadraque", "Mesaque", "Abede-Nego"],
        "tema": "Fidelidade ainda que não nos livre",
    },
    {
        "id": "jonas",
        "titulo": "Jonas e o Grande Peixe",
        "referencia": "Livro de Jonas",
        "personagens_principais": ["Jonas"],
        "tema": "Fugir de Deus, segunda chance, misericórdia",
    },
    {
        "id": "isaias_chamado",
        "titulo": "A Visão e o Chamado de Isaías",
        "referencia": "Isaías 6",
        "personagens_principais": ["Isaías"],
        "tema": "Santidade, perdão, disponibilidade",
    },
    {
        "id": "ezequiel_ossos",
        "titulo": "Ezequiel e o Vale de Ossos Secos",
        "referencia": "Ezequiel 37",
        "personagens_principais": ["Ezequiel"],
        "tema": "Restauração do que parece morto",
    },

    # ---------------- Novo Testamento ----------------
    {
        "id": "anunciacao",
        "titulo": "A Anunciação a Maria",
        "referencia": "Lucas 1",
        "personagens_principais": ["Maria", "Anjo Gabriel"],
        "tema": "Disponibilidade, fé jovem",
    },
    {
        "id": "natal",
        "titulo": "O Nascimento de Jesus",
        "referencia": "Lucas 2",
        "personagens_principais": ["Jesus", "Maria", "José"],
        "tema": "Humildade do Salvador, encarnação",
    },
    {
        "id": "magos",
        "titulo": "Os Magos Visitam Jesus",
        "referencia": "Mateus 2",
        "personagens_principais": ["Magos do Oriente", "Jesus", "Herodes"],
        "tema": "Busca sincera, adoração",
    },
    {
        "id": "batismo_jesus",
        "titulo": "O Batismo de Jesus",
        "referencia": "Mateus 3",
        "personagens_principais": ["Jesus", "João Batista"],
        "tema": "Identidade declarada pelo Pai",
    },
    {
        "id": "tentacao_deserto",
        "titulo": "Jesus Tentado no Deserto",
        "referencia": "Mateus 4",
        "personagens_principais": ["Jesus"],
        "tema": "Resistência pela Palavra, propósito",
    },
    {
        "id": "vocacao_pescadores",
        "titulo": "A Vocação dos Pescadores",
        "referencia": "Lucas 5",
        "personagens_principais": ["Pedro", "Tiago", "João", "Jesus"],
        "tema": "Largar tudo para seguir",
    },
    {
        "id": "sermao_monte",
        "titulo": "O Sermão do Monte",
        "referencia": "Mateus 5-7",
        "personagens_principais": ["Jesus"],
        "tema": "Bem-aventuranças, ética do Reino",
    },
    {
        "id": "tempestade_acalmada",
        "titulo": "Jesus Acalma a Tempestade",
        "referencia": "Marcos 4",
        "personagens_principais": ["Jesus", "Discípulos"],
        "tema": "Medo, autoridade sobre o caos",
    },
    {
        "id": "multiplicacao_paes",
        "titulo": "A Multiplicação dos Pães",
        "referencia": "João 6",
        "personagens_principais": ["Jesus", "Discípulos", "Multidão"],
        "tema": "Provisão a partir do pouco",
    },
    {
        "id": "jesus_anda_aguas",
        "titulo": "Jesus Anda Sobre as Águas",
        "referencia": "Mateus 14",
        "personagens_principais": ["Jesus", "Pedro"],
        "tema": "Olhar fixo, dúvida e socorro",
    },
    {
        "id": "samaritana_poco",
        "titulo": "A Samaritana no Poço",
        "referencia": "João 4",
        "personagens_principais": ["Jesus", "Samaritana"],
        "tema": "Sede profunda, encontro restaurador",
    },
    {
        "id": "filho_prodigo",
        "titulo": "O Filho Pródigo",
        "referencia": "Lucas 15",
        "personagens_principais": ["Pai", "Filho mais novo", "Filho mais velho"],
        "tema": "Volta para casa, perdão do pai",
    },
    {
        "id": "bom_samaritano",
        "titulo": "O Bom Samaritano",
        "referencia": "Lucas 10",
        "personagens_principais": ["Samaritano", "Ferido", "Sacerdote", "Levita"],
        "tema": "Compaixão atravessa barreiras",
    },
    {
        "id": "zaqueu",
        "titulo": "Zaqueu, o Cobrador de Impostos",
        "referencia": "Lucas 19",
        "personagens_principais": ["Zaqueu", "Jesus"],
        "tema": "Conversão e restituição",
    },
    {
        "id": "lazaro",
        "titulo": "A Ressurreição de Lázaro",
        "referencia": "João 11",
        "personagens_principais": ["Jesus", "Lázaro", "Marta", "Maria"],
        "tema": "Vida onde só há luto",
    },
    {
        "id": "ultima_ceia",
        "titulo": "A Última Ceia",
        "referencia": "Lucas 22",
        "personagens_principais": ["Jesus", "Discípulos"],
        "tema": "Serviço, lembrança, entrega",
    },
    {
        "id": "getsemani",
        "titulo": "Jesus no Getsêmani",
        "referencia": "Mateus 26",
        "personagens_principais": ["Jesus"],
        "tema": "Angústia, submissão à vontade do Pai",
    },
    {
        "id": "crucificacao",
        "titulo": "A Crucificação de Jesus",
        "referencia": "João 19",
        "personagens_principais": ["Jesus"],
        "tema": "Sacrifício, perdão até o fim",
    },
    {
        "id": "ressurreicao",
        "titulo": "A Ressurreição de Jesus",
        "referencia": "Mateus 28",
        "personagens_principais": ["Jesus", "Maria Madalena"],
        "tema": "Vitória sobre a morte, esperança",
    },
    {
        "id": "emaus",
        "titulo": "Os Discípulos de Emaús",
        "referencia": "Lucas 24",
        "personagens_principais": ["Cleopas", "Outro discípulo", "Jesus"],
        "tema": "Reconhecer Jesus na caminhada",
    },
    {
        "id": "pentecostes",
        "titulo": "O Dia de Pentecostes",
        "referencia": "Atos 2",
        "personagens_principais": ["Apóstolos", "Pedro"],
        "tema": "Espírito Santo, nascimento da Igreja",
    },
    {
        "id": "conversao_paulo",
        "titulo": "A Conversão de Paulo",
        "referencia": "Atos 9",
        "personagens_principais": ["Saulo de Tarso", "Ananias"],
        "tema": "Encontro que muda a vida",
    },
    {
        "id": "pedro_prisao",
        "titulo": "Pedro Libertado da Prisão",
        "referencia": "Atos 12",
        "personagens_principais": ["Pedro"],
        "tema": "Oração da igreja, livramento",
    },
]


# =========================================================================
# Função principal
# =========================================================================
def escolher_historia(historias_recentes: Optional[list[str]] = None) -> dict:
    """
    Pede ao Claude que escolha UMA história da lista de referência, evitando
    repetir IDs presentes em `historias_recentes`.

    Retorna o dict completo da história escolhida, acrescido de um campo
    `motivo` com a justificativa curta do modelo.

    Args:
        historias_recentes: lista opcional de IDs já contadas (últimas 20 etc.).
                            Se None, o modelo escolhe livremente.

    Raises:
        RuntimeError: se a resposta do Claude não puder ser parseada ou
                      apontar para um ID inexistente.
    """
    historias_recentes = historias_recentes or []

    cliente = Anthropic()

    # Inclui só id + titulo + tema no prompt, para manter o contexto curto.
    pool = [
        {"id": h["id"], "titulo": h["titulo"], "tema": h["tema"]}
        for h in HISTORIAS_REFERENCIA
        if h["id"] not in historias_recentes
    ]

    # Se quase tudo já foi contado, libera todas (evita travar a pipeline).
    if not pool:
        pool = [
            {"id": h["id"], "titulo": h["titulo"], "tema": h["tema"]}
            for h in HISTORIAS_REFERENCIA
        ]

    system_prompt = (
        "Você é um curador de conteúdo bíblico para vídeos curtos de redes sociais. "
        "Sua tarefa é escolher UMA história da lista fornecida que tenha alto "
        "potencial de engajamento hoje: histórias com conflito claro, virada "
        "emocional, lição prática e familiaridade para o público brasileiro. "
        "Equilibre histórias muito conhecidas com algumas menos óbvias para "
        "manter variedade ao longo do tempo."
    )

    user_prompt = (
        "Escolha exatamente uma história da lista abaixo. Retorne APENAS um "
        "objeto JSON válido, sem comentários, sem texto antes ou depois, "
        "com a forma:\n"
        '{"id": "<id_da_historia>", "motivo": "<uma frase curta justificando>"}\n\n'
        f"Lista disponível (JSON):\n{json.dumps(pool, ensure_ascii=False)}"
    )

    resposta = cliente.messages.create(
        model=MODELO_ESCOLHA,
        max_tokens=300,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    texto = resposta.content[0].text.strip()

    # Tolerância a respostas em blocos de código.
    if texto.startswith("```"):
        texto = texto.strip("`")
        if texto.startswith("json"):
            texto = texto[4:]
        texto = texto.strip()

    try:
        escolha = json.loads(texto)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Resposta do Claude não é JSON válido: {texto!r}"
        ) from e

    id_escolhido = escolha.get("id")
    motivo = escolha.get("motivo", "")

    historia = next(
        (h for h in HISTORIAS_REFERENCIA if h["id"] == id_escolhido), None
    )
    if historia is None:
        raise RuntimeError(
            f"Claude retornou id desconhecido: {id_escolhido!r}"
        )

    # Cópia rasa + campo motivo, para não mutar a constante.
    resultado = dict(historia)
    resultado["motivo"] = motivo
    return resultado


# =========================================================================
# Teste rápido isolado
# =========================================================================
if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY não configurada no .env")

    print(f"Pool total: {len(HISTORIAS_REFERENCIA)} histórias")
    print("Pedindo uma escolha ao Claude...")
    h = escolher_historia(historias_recentes=["davi_golias", "noe_arca"])
    print(json.dumps(h, ensure_ascii=False, indent=2))
