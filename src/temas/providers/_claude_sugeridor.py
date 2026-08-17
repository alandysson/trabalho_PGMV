"""Implementação concreta de `SugeridorHistoriaProtocol` usando Anthropic.

Usa o modelo Haiku (rápido e barato — ~$0,003 por sugestão). É chamado
**raramente**: só quando `escolher_historia` filtrou todo o pool por
`ids_recentes`. Resultado é cacheado em `historias_sugeridas`, então
ao longo do tempo o catálogo cresce sem novas chamadas.

Falhas (sem chave, timeout, JSON mal formado) levantam `FalhaSugestao`
— o provider trata como sinal pra cair no fallback (sortear do pool
ignorando recentes).

NÃO usado em runtime quente das requests autenticadas: a chamada
acontece dentro de `escolher_historia`, que só é invocado pela feature
`videos` ao começar um job em background. Não bloqueia o pipeline
síncrono de `/temas`.
"""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING

from src.temas.domain.entities import HistoriaEscolhida
from src.temas.domain.sugeridor_protocol import ContextoSugestao, FalhaSugestao

if TYPE_CHECKING:
    from anthropic import Anthropic


_MODELO_PADRAO = "claude-haiku-4-5-20251001"
_MAX_TOKENS = 400


_SYSTEM = """Você é um curador de histórias para vídeos curtos.

Sua tarefa é propor UMA nova história sobre um tema específico,
**diferente** das histórias já existentes que serão informadas.

REGRAS:
- A história deve ser autêntica do tema (não invente fato fictício
  apresentando como real).
- Não repita nenhum ID listado em "ids_a_evitar".
- O `id` retornado deve ser snake_case curto e estável (ex.: "abel_e_caim").

Responda **estritamente** com um objeto JSON no formato:

{
  "id": "snake_case_curto",
  "titulo": "Título Bonito da História",
  "referencia": "Origem / Livro / Tradição",
  "personagens": ["Personagem 1", "Personagem 2"],
  "tema_central": "palavra ou frase curta"
}

Sem prosa, sem markdown, sem cercas de código. Apenas o JSON.
"""


_REGEX_JSON = re.compile(r"\{.*\}", re.DOTALL)


class ClaudeSugeridor:
    def __init__(
        self,
        client: "Anthropic",
        modelo: str = _MODELO_PADRAO,
        logger: logging.Logger | None = None,
    ) -> None:
        self._client = client
        self._modelo = modelo
        self._log = logger or logging.getLogger(__name__)

    def sugerir(self, contexto: ContextoSugestao) -> HistoriaEscolhida:
        prompt_usuario = self._montar_user_prompt(contexto)
        try:
            resposta = self._client.messages.create(
                model=self._modelo,
                max_tokens=_MAX_TOKENS,
                system=[
                    {
                        "type": "text",
                        "text": _SYSTEM,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": prompt_usuario}],
            )
        except Exception as exc:
            self._log.warning("ClaudeSugeridor falhou na chamada: %s", exc)
            raise FalhaSugestao(str(exc)) from exc

        try:
            texto = resposta.content[0].text  # type: ignore[attr-defined]
        except (AttributeError, IndexError) as exc:
            raise FalhaSugestao(f"Resposta sem texto utilizável: {exc}") from exc

        return self._parse(texto)

    @staticmethod
    def _montar_user_prompt(c: ContextoSugestao) -> str:
        evitar = ", ".join(c.ids_a_evitar[:50]) or "(nenhum)"
        exemplos = ", ".join(c.exemplos_existentes[:20]) or "(nenhum)"
        return (
            f"Tema: {c.tema_nome} (id: {c.tema_id})\n"
            f"Exemplos do catálogo curado: {exemplos}\n"
            f"ids_a_evitar: {evitar}\n\n"
            f"Proponha uma história nova, fora dessa lista, autêntica do tema. "
            f"Retorne apenas o JSON especificado."
        )

    @staticmethod
    def _parse(texto: str) -> HistoriaEscolhida:
        m = _REGEX_JSON.search(texto)
        if not m:
            raise FalhaSugestao("Resposta não contém JSON")
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError as exc:
            raise FalhaSugestao(f"JSON inválido: {exc}") from exc

        try:
            return HistoriaEscolhida(
                id=str(data["id"]).strip(),
                titulo=str(data["titulo"]).strip(),
                referencia=str(data.get("referencia", "")).strip(),
                personagens=[str(p) for p in data.get("personagens", [])],
                tema_central=str(data.get("tema_central", "")).strip(),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise FalhaSugestao(f"Campos do JSON inválidos: {exc}") from exc
