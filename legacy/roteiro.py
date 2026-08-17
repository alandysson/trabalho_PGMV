"""
Geração de roteiro e divisão em cenas via Claude.

Dois pontos de contato com a API:

  - `gerar_roteiro(historia)` — escreve um texto narrável de 130-160 palavras,
    com hook forte e ritmo de oralidade. Vale pagar Sonnet aqui porque a
    qualidade do roteiro determina a qualidade percebida do vídeo final.

  - `gerar_cenas(roteiro, num_cenas)` — divide o roteiro em N cenas e gera
    uma query de busca em INGLÊS para cada uma (Pexels indexa em inglês).
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from anthropic import Anthropic


MODELO_ROTEIRO = "claude-sonnet-4-6"
MODELO_CENAS = "claude-haiku-4-5"
MODELO_POST = "claude-sonnet-4-6"


# =========================================================================
# Regras teológicas comuns aos dois prompts.
# =========================================================================
REGRAS_TEOLOGICAS = (
    "REGRAS TEOLÓGICAS OBRIGATÓRIAS:\n"
    "- Fiel ao texto bíblico; não invente fatos, falas ou cenas que não "
    "estejam na narrativa original.\n"
    "- Sem teologia da prosperidade (nada de 'Deus vai te dar dinheiro/cura "
    "se você crer').\n"
    "- Sem posicionamento denominacional (católico vs. evangélico vs. "
    "pentecostal) nem político.\n"
    "- Sem juízo agressivo sobre outras religiões ou descrentes.\n"
    "- Tom acolhedor, respeitoso, que sirva tanto a religiosos quanto a "
    "pessoas em busca."
)


def _extrair_json(texto: str) -> Any:
    """
    Extrai um objeto/array JSON de uma string que pode vir embrulhada em
    blocos ```json ... ``` ou conter prefácio.
    """
    texto = texto.strip()
    if texto.startswith("```"):
        texto = texto.strip("`")
        if texto.startswith("json"):
            texto = texto[4:]
        texto = texto.strip()

    # Tenta o parse direto primeiro.
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        pass

    # Fallback: tenta achar o primeiro objeto/array JSON dentro do texto.
    match = re.search(r"(\{.*\}|\[.*\])", texto, flags=re.DOTALL)
    if not match:
        raise RuntimeError(f"Não foi possível extrair JSON da resposta:\n{texto!r}")
    return json.loads(match.group(1))


# =========================================================================
# Roteiro
# =========================================================================
def gerar_roteiro(historia: dict) -> dict:
    """
    Gera o roteiro narrável para a história passada.

    Args:
        historia: dict da história (id, titulo, referencia, personagens, tema).

    Returns:
        dict com chaves:
          - texto: o roteiro completo, pronto para TTS.
          - titulo: título usado no roteiro (pode coincidir com historia['titulo']).
          - palavras: contagem de palavras.
    """
    cliente = Anthropic()

    system_prompt = (
        "Você é um roteirista profissional especializado em vídeos curtos "
        "(50-70 segundos) sobre histórias bíblicas para Kwai e TikTok. "
        "Seu objetivo é prender a atenção desde o primeiro segundo e "
        "entregar uma narrativa completa em poucas palavras.\n\n"
        "DIRETRIZES DE ESCRITA:\n"
        "- 130 a 160 palavras no total (gera ~50-70s de áudio em ritmo natural).\n"
        "- HOOK obrigatório nos primeiros 3 segundos: uma pergunta provocativa, "
        "uma afirmação surpreendente ou uma cena visual forte. Nunca comece "
        "com 'Olá', 'Vou contar', 'Hoje vamos falar'.\n"
        "- Estrutura: hook → contexto rápido → conflito → clímax → desfecho com "
        "aplicação curta para a vida hoje.\n"
        "- Português brasileiro coloquial, frases curtas, ritmo de oralidade. "
        "Pense em narrar em voz alta, não escrever um parágrafo literário.\n"
        "- Sem palavras estrangeiras, sem latim, sem 'shalom', 'aleluia' etc.\n"
        "- Sem números difíceis de pronunciar: escreva 'cinco mil' em vez de "
        "'5000', 'trinta anos' em vez de '30 anos'.\n"
        "- Sem abreviações ('São Paulo' não 'SP', 'capítulo' não 'cap.').\n"
        "- Pontuação cuidadosa: vírgulas e pontos finais servem como respirações "
        "para o TTS. Evite reticências, travessões e parênteses.\n"
        "- Não inclua marcações de cena, indicações sonoras, nem 'fade in'. "
        "Apenas o TEXTO QUE SERÁ NARRADO.\n\n"
        + REGRAS_TEOLOGICAS
    )

    user_prompt = (
        f"Escreva o roteiro narrável para a história:\n\n"
        f"- Título: {historia['titulo']}\n"
        f"- Referência: {historia['referencia']}\n"
        f"- Personagens: {', '.join(historia['personagens_principais'])}\n"
        f"- Tema: {historia['tema']}\n\n"
        "Retorne APENAS um JSON válido, sem texto antes ou depois, no formato:\n"
        '{"titulo": "<título curto e chamativo>", "texto": "<roteiro completo>"}'
    )

    resp = cliente.messages.create(
        model=MODELO_ROTEIRO,
        max_tokens=1500,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    dados = _extrair_json(resp.content[0].text)
    texto = (dados.get("texto") or "").strip()
    titulo = (dados.get("titulo") or historia["titulo"]).strip()

    if not texto:
        raise RuntimeError(f"Roteiro vazio na resposta: {dados!r}")

    palavras = len(texto.split())

    return {
        "titulo": titulo,
        "texto": texto,
        "palavras": palavras,
    }


# =========================================================================
# Cenas
# =========================================================================
def gerar_cenas(roteiro: str, num_cenas: int = 6) -> list[dict]:
    """
    Divide o roteiro em `num_cenas` cenas, gerando uma query de busca em
    inglês para cada uma (apropriada ao Pexels Videos).

    Cada cena retornada tem:
      - ordem: int (1..N)
      - trecho_texto: trecho EXATO do roteiro que a cena cobre
      - query_pexels: query em inglês, 2-4 palavras concretas e visuais
      - descricao_visual: descrição curta em português (debug)
    """
    if num_cenas < 3 or num_cenas > 10:
        raise ValueError("num_cenas deve estar entre 3 e 10")

    cliente = Anthropic()

    system_prompt = (
        "Você é um diretor de arte de vídeos curtos verticais. Dado um "
        "roteiro de narração, você divide o texto em cenas visuais e gera "
        "uma query de busca em INGLÊS para cada cena, otimizada para "
        "encontrar vídeos stock no Pexels.\n\n"
        "DIRETRIZES DE QUERY:\n"
        "- 2 a 4 palavras em inglês.\n"
        "- Sempre CONCRETAS e VISUAIS: pessoas, objetos, lugares, fenômenos "
        "naturais. Exemplos bons: 'ancient stone temple', 'desert sunset "
        "silhouette', 'stormy ocean waves', 'olive tree branches', "
        "'warrior holding sword', 'shepherd walking sheep'.\n"
        "- NUNCA use termos abstratos: nada de 'faith', 'hope', 'sin', "
        "'redemption', 'forgiveness'. Eles não retornam imagens úteis.\n"
        "- Evite nomes próprios bíblicos como query (Pexels não indexa "
        "'Moses' como vídeo). Use o que a cena VISUALMENTE mostra.\n"
        "- Prefira ambientes do antigo Oriente Médio quando fizer sentido: "
        "deserto, pedras, fogo, água, oliveiras, animais de pastoreio."
    )

    user_prompt = (
        f"Divida o roteiro abaixo em exatamente {num_cenas} cenas "
        "sequenciais. Os trechos de texto devem ser EXATOS (copiados sem "
        "alteração) e cobrir o roteiro inteiro, em ordem, sem sobreposição "
        "nem buraco.\n\n"
        f"ROTEIRO:\n{roteiro}\n\n"
        "Retorne APENAS um array JSON válido, sem texto antes ou depois, "
        "no formato:\n"
        "[\n"
        "  {\n"
        '    "ordem": 1,\n'
        '    "trecho_texto": "...",\n'
        '    "query_pexels": "...",\n'
        '    "descricao_visual": "..."\n'
        "  },\n"
        "  ...\n"
        "]"
    )

    resp = cliente.messages.create(
        model=MODELO_CENAS,
        max_tokens=2500,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    cenas = _extrair_json(resp.content[0].text)

    if not isinstance(cenas, list):
        raise RuntimeError(f"Esperava array de cenas, veio: {type(cenas)}")

    # Validação leve dos campos.
    obrigatorios = {"ordem", "trecho_texto", "query_pexels", "descricao_visual"}
    for cena in cenas:
        faltando = obrigatorios - set(cena.keys())
        if faltando:
            raise RuntimeError(f"Cena com campos faltando {faltando}: {cena}")

    # Garante ordenação por `ordem`.
    cenas.sort(key=lambda c: c["ordem"])

    return cenas


# =========================================================================
# Postagem (legenda + hashtags) para Kwai/TikTok
# =========================================================================
def gerar_post(historia: dict, roteiro: dict) -> dict:
    """
    Gera o texto pronto para copiar e colar na descrição do Kwai/TikTok.

    Args:
        historia: dict da história (titulo, referencia, tema...).
        roteiro: dict retornado por `gerar_roteiro` (titulo + texto).

    Returns:
        dict com chaves:
          - legenda: 1-3 linhas curtas com hook + CTA (sem hashtags).
          - hashtags: lista de strings começando com '#'.
    """
    cliente = Anthropic()

    system_prompt = (
        "Você é um social media manager especializado em conteúdo bíblico "
        "para Kwai e TikTok no Brasil. Sua tarefa é criar a descrição/legenda "
        "da postagem de um vídeo curto, otimizada para retenção e alcance.\n\n"
        "DIRETRIZES DE LEGENDA:\n"
        "- 1 a 3 linhas curtas, no máximo 220 caracteres no total.\n"
        "- A primeira linha é um HOOK: pergunta provocativa ou afirmação "
        "que gera curiosidade. Nunca comece com 'Confira', 'Assista', "
        "'Olá pessoal'.\n"
        "- Termine com um CTA curto convidando a comentar, salvar ou "
        "compartilhar (varie — não use sempre o mesmo).\n"
        "- Português brasileiro coloquial. Sem emojis exagerados (no máximo 2).\n"
        "- Pode citar a referência bíblica de forma natural se couber.\n\n"
        "DIRETRIZES DE HASHTAGS:\n"
        "- 5 hashtags, todas começando com '#', sem espaços internos.\n"
        "- Mistura: amplas e populares (#biblia, #fe, #jesus, #deus, "
        "#cristao), específicas da história/tema, de formato/nicho"
        "- Sem hashtags genéricas tipo #fyp, #viral, #parati (algoritmos "
        "dos apps brasileiros já penalizam isso).\n"
        "- Tudo em minúsculas, sem acentos nas hashtags (#fe, não #fé)."
    )

    user_prompt = (
        f"História: {historia['titulo']}\n"
        f"Referência: {historia['referencia']}\n"
        f"Tema: {historia.get('tema', '')}\n\n"
        f"Roteiro do vídeo (para você captar o tom e a mensagem):\n"
        f"{roteiro['texto']}\n\n"
        "Retorne APENAS um JSON válido, sem texto antes ou depois, no formato:\n"
        '{"legenda": "<texto da legenda com quebras de linha\\n quando fizer sentido>", '
        '"hashtags": ["#exemplo1", "#exemplo2", "..."]}'
    )

    resp = cliente.messages.create(
        model=MODELO_POST,
        max_tokens=1000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    dados = _extrair_json(resp.content[0].text)
    legenda = (dados.get("legenda") or "").strip()
    hashtags = dados.get("hashtags") or []

    if not legenda:
        raise RuntimeError(f"Legenda vazia na resposta: {dados!r}")
    if not isinstance(hashtags, list) or not hashtags:
        raise RuntimeError(f"Hashtags ausentes ou inválidas: {dados!r}")

    # Normaliza: garante '#' inicial, remove espaços internos, minúsculas.
    hashtags_norm: list[str] = []
    for h in hashtags:
        if not isinstance(h, str):
            continue
        t = h.strip().lower().replace(" ", "")
        if not t:
            continue
        if not t.startswith("#"):
            t = "#" + t
        hashtags_norm.append(t)
    # Deduplica preservando ordem.
    hashtags_norm = list(dict.fromkeys(hashtags_norm))

    return {
        "legenda": legenda,
        "hashtags": hashtags_norm,
    }


# =========================================================================
# Teste rápido isolado
# =========================================================================
if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY não configurada")

    historia_teste = {
        "id": "davi_golias",
        "titulo": "Davi e Golias",
        "referencia": "1 Samuel 17",
        "personagens_principais": ["Davi", "Golias"],
        "tema": "Coragem, fé contra gigantes",
    }

    print("[1] Gerando roteiro...")
    r = gerar_roteiro(historia_teste)
    print(f"Título: {r['titulo']}")
    print(f"Palavras: {r['palavras']}")
    print(f"Texto:\n{r['texto']}\n")

    print("[2] Gerando cenas...")
    cenas = gerar_cenas(r["texto"], num_cenas=6)
    print(json.dumps(cenas, ensure_ascii=False, indent=2))

    print("[3] Gerando postagem...")
    post = gerar_post(historia_teste, r)
    print(json.dumps(post, ensure_ascii=False, indent=2))
