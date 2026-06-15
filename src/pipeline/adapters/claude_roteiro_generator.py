"""Gera roteiro + cenas via Claude (Anthropic).

Generalização do `legacy/roteiro.py`: o system prompt do roteiro NÃO é
mais hardcoded bíblico — vem do tema (provider.system_prompt_roteiro()).
O prompt das cenas continua aqui (regras de busca no Pexels são
agnósticas ao tema, com hints visuais passados como parâmetro).
"""

from __future__ import annotations

import json
import re
from typing import Any

from src.pipeline.domain.entities import Cena, Post, Roteiro


_MODELO_ROTEIRO = "claude-sonnet-4-6"
_MODELO_CENAS = "claude-haiku-4-5-20251001"
_MODELO_POST = "claude-haiku-4-5-20251001"


_SYSTEM_POST = (
    "Você é um social media manager especializado em vídeos curtos pra "
    "Kwai e TikTok no Brasil. Cria a legenda da postagem + 5 hashtags "
    "específicas do tema do vídeo.\n\n"
    "DIRETRIZES DE LEGENDA:\n"
    "- 1 a 3 linhas curtas, máximo 220 caracteres no total.\n"
    "- 1ª linha é HOOK: pergunta provocativa, afirmação que gera "
    "curiosidade, ou cena visual marcante. NUNCA comece com 'Confira', "
    "'Assista', 'Olá pessoal'.\n"
    "- Termine com CTA curto (comentar, salvar, compartilhar — varie).\n"
    "- Português brasileiro coloquial; no máximo 2 emojis (opcional).\n"
    "- Pode citar a referência da história se couber naturalmente.\n\n"
    "DIRETRIZES DE HASHTAGS:\n"
    "- EXATAMENTE 5 hashtags, todas relacionadas ao TEMA do vídeo + à "
    "história específica.\n"
    "- Comece com '#', sem espaços internos, minúsculas, sem acentos "
    "(#fe, não #fé).\n"
    "- Mistura recomendada: 2-3 amplas e populares do tema + 2-3 "
    "específicas da história ou conceito central.\n"
    "- NÃO use hashtags genéricas tipo #fyp, #viral, #parati (algoritmos "
    "brasileiros penalizam).\n"
    "- NÃO use hashtags fora do tema (não force #motivacional num vídeo "
    "de fábula se não vier ao caso).\n"
)


_SYSTEM_CENAS_BASE = (
    "Você é um diretor de arte de vídeos curtos verticais. Dado um "
    "roteiro de narração, você divide o texto em cenas visuais e gera "
    "uma query de busca em INGLÊS para cada cena, otimizada para "
    "encontrar vídeos stock no Pexels.\n\n"
    "DIRETRIZES DE QUERY:\n"
    "- 2 a 4 palavras em inglês.\n"
    "- Sempre CONCRETAS e VISUAIS (pessoas, objetos, lugares, fenômenos "
    "naturais).\n"
    "- NUNCA use termos abstratos (faith, hope, sin, virtue) — não retornam "
    "imagens úteis.\n"
    "- Evite nomes próprios (Pexels não indexa nomes individuais).\n"
)


def _extrair_json(texto: str) -> Any:
    texto = texto.strip()
    if texto.startswith("```"):
        texto = texto.strip("`")
        if texto.startswith("json"):
            texto = texto[4:]
        texto = texto.strip()
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        pass
    match = re.search(r"(\{.*\}|\[.*\])", texto, flags=re.DOTALL)
    if not match:
        raise RuntimeError(f"Resposta sem JSON utilizável: {texto!r}")
    return json.loads(match.group(1))


class ClaudeRoteiroGenerator:
    def __init__(
        self,
        client,
        modelo_roteiro: str = _MODELO_ROTEIRO,
        modelo_cenas: str = _MODELO_CENAS,
        modelo_post: str = _MODELO_POST,
    ) -> None:
        self._client = client
        self._modelo_roteiro = modelo_roteiro
        self._modelo_cenas = modelo_cenas
        self._modelo_post = modelo_post

    def gerar_roteiro(
        self,
        *,
        titulo: str,
        referencia: str,
        personagens: list[str],
        tema_central: str,
        system_prompt: str,
    ) -> Roteiro:
        user_prompt = (
            f"Escreva o roteiro narrável para a história:\n\n"
            f"- Título: {titulo}\n"
            f"- Referência: {referencia}\n"
            f"- Personagens: {', '.join(personagens) or '(não especificado)'}\n"
            f"- Tema central: {tema_central}\n\n"
            "Retorne APENAS um JSON válido, sem texto antes ou depois, no formato:\n"
            '{"titulo": "<título curto e chamativo>", "texto": "<roteiro completo>"}'
        )
        resp = self._client.messages.create(
            model=self._modelo_roteiro,
            max_tokens=1500,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        dados = _extrair_json(resp.content[0].text)
        texto = (dados.get("texto") or "").strip()
        titulo_final = (dados.get("titulo") or titulo).strip()
        if not texto:
            raise RuntimeError(f"Roteiro vazio: {dados!r}")
        return Roteiro(titulo=titulo_final, texto=texto, palavras=len(texto.split()))

    def gerar_cenas(
        self,
        *,
        roteiro: str,
        num_cenas: int,
        dicas_visuais: str,
    ) -> list[Cena]:
        if num_cenas < 3 or num_cenas > 10:
            raise ValueError("num_cenas deve estar entre 3 e 10")

        system = _SYSTEM_CENAS_BASE
        if dicas_visuais:
            system += f"\nDICAS VISUAIS DO TEMA (use como referência de ambientação):\n{dicas_visuais}\n"

        user_prompt = (
            f"Divida o roteiro abaixo em exatamente {num_cenas} cenas "
            "sequenciais. Os trechos de texto devem ser EXATOS (copiados sem "
            "alteração) e cobrir o roteiro inteiro, em ordem, sem sobreposição "
            "nem buraco.\n\n"
            f"ROTEIRO:\n{roteiro}\n\n"
            "Retorne APENAS um array JSON válido, sem texto antes ou depois, "
            'no formato: [{"ordem":1,"trecho_texto":"...","query_pexels":"...",'
            '"descricao_visual":"..."}, ...]'
        )

        resp = self._client.messages.create(
            model=self._modelo_cenas,
            max_tokens=2500,
            system=system,
            messages=[{"role": "user", "content": user_prompt}],
        )
        bruto = _extrair_json(resp.content[0].text)
        if not isinstance(bruto, list):
            raise RuntimeError(f"Esperava array de cenas, veio: {type(bruto)}")

        cenas: list[Cena] = []
        for c in bruto:
            try:
                cenas.append(
                    Cena(
                        ordem=int(c["ordem"]),
                        trecho_texto=str(c["trecho_texto"]).strip(),
                        query_pexels=str(c["query_pexels"]).strip(),
                        descricao_visual=str(c.get("descricao_visual", "")).strip(),
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise RuntimeError(f"Cena malformada: {c} | {exc}") from exc

        cenas.sort(key=lambda c: c.ordem)
        return cenas

    def gerar_post(
        self,
        *,
        titulo: str,
        referencia: str,
        tema_central: str,
        tema_nome: str,
        roteiro: str,
    ) -> Post:
        user_prompt = (
            f"TEMA do canal: {tema_nome}\n"
            f"História: {titulo}\n"
            f"Referência: {referencia}\n"
            f"Conceito central: {tema_central or '(não informado)'}\n\n"
            f"Roteiro do vídeo (use pra captar tom e mensagem):\n{roteiro}\n\n"
            "Retorne APENAS um JSON válido, sem texto antes ou depois, "
            "no formato:\n"
            '{"legenda":"<texto da legenda com \\n quando fizer sentido>",'
            '"hashtags":["#exemplo1","#exemplo2","#exemplo3","#exemplo4","#exemplo5"]}'
        )

        resp = self._client.messages.create(
            model=self._modelo_post,
            max_tokens=800,
            system=_SYSTEM_POST,
            messages=[{"role": "user", "content": user_prompt}],
        )
        dados = _extrair_json(resp.content[0].text)

        legenda = (dados.get("legenda") or "").strip()
        if not legenda:
            raise RuntimeError(f"Legenda vazia: {dados!r}")

        hashtags_brutas = dados.get("hashtags") or []
        if not isinstance(hashtags_brutas, list):
            raise RuntimeError(f"hashtags inválidas: {dados!r}")

        hashtags = _normalizar_hashtags(hashtags_brutas)
        if not hashtags:
            raise RuntimeError(f"Nenhuma hashtag válida em {dados!r}")

        # Garante exatamente 5 — corta excesso, e se vier menos, mantém o
        # que tem (não inventa do nosso lado).
        return Post(legenda=legenda, hashtags=hashtags[:5])


def _normalizar_hashtags(brutas: list) -> list[str]:
    saida: list[str] = []
    for h in brutas:
        if not isinstance(h, str):
            continue
        t = h.strip().lower().replace(" ", "")
        if not t:
            continue
        if not t.startswith("#"):
            t = "#" + t
        saida.append(t)
    # Deduplica preservando ordem.
    return list(dict.fromkeys(saida))
