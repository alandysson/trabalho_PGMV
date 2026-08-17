"""
Integração com a Pexels Videos API.

Responsável por:
  - Buscar vídeos verticais (portrait) por query em inglês.
  - Baixar o arquivo escolhido em qualidade ~HD vertical (1080p).
  - Registrar metadados de atribuição (obrigatório pelos termos da Pexels).

A API exige a chave no header `Authorization` direto (sem "Bearer").
Rate limit do plano gratuito: 200 req/h, 20.000/mês — não chega perto
em uso normal (uma execução faz ~6-12 requests).
"""

from __future__ import annotations

import os
import random
import time
from pathlib import Path
from typing import Optional

import requests


PEXELS_BASE_URL = "https://api.pexels.com/videos/search"

# Pausa entre requests para ser educado com a API.
PAUSA_ENTRE_REQUESTS_S = 0.5


def _headers() -> dict:
    chave = os.environ.get("PEXELS_API_KEY")
    if not chave:
        raise RuntimeError("PEXELS_API_KEY não configurada no .env")
    return {"Authorization": chave}


def buscar_video(
    query: str,
    duracao_minima: int = 4,
    orientacao: str = "portrait",
) -> Optional[dict]:
    """
    Faz uma busca por vídeos no Pexels e seleciona um candidato adequado.

    A lógica de escolha:
      - Pede 10 resultados ordenados por relevância.
      - Filtra por duração ≥ `duracao_minima`.
      - Sorteia aleatoriamente entre os 5 primeiros válidos (para variedade
        entre execuções com a mesma query).
      - Dentro do vídeo escolhido, pega a melhor `video_file` com largura
        próxima de 1080px (HD vertical).

    Returns:
        dict com chaves: url_download, duracao, largura, altura, id_pexels,
        fotografo_nome, fotografo_url, pexels_url.
        Ou None se nenhum resultado for adequado.
    """
    params = {
        "query": query,
        "orientation": orientacao,
        "size": "medium",
        "per_page": 10,
    }

    resp = requests.get(
        PEXELS_BASE_URL, headers=_headers(), params=params, timeout=30
    )
    time.sleep(PAUSA_ENTRE_REQUESTS_S)

    if resp.status_code != 200:
        print(
            f"  [pexels] busca falhou (HTTP {resp.status_code}) para query "
            f"'{query}': {resp.text[:200]}"
        )
        return None

    dados = resp.json()
    videos = dados.get("videos", [])

    candidatos = [v for v in videos if v.get("duration", 0) >= duracao_minima]
    if not candidatos:
        return None

    # Sorteio entre os 5 primeiros — relevância preservada + variedade.
    candidatos = candidatos[:5]
    escolhido = random.choice(candidatos)

    arquivo = _melhor_arquivo_vertical(escolhido.get("video_files", []))
    if arquivo is None:
        return None

    return {
        "url_download": arquivo["link"],
        "duracao": escolhido.get("duration"),
        "largura": arquivo.get("width"),
        "altura": arquivo.get("height"),
        "id_pexels": escolhido.get("id"),
        "fotografo_nome": escolhido.get("user", {}).get("name", "desconhecido"),
        "fotografo_url": escolhido.get("user", {}).get("url", ""),
        "pexels_url": escolhido.get("url", ""),
    }


def _melhor_arquivo_vertical(arquivos: list[dict]) -> Optional[dict]:
    """
    Seleciona o melhor `video_file` para uso vertical.

    Estratégia: prefere o arquivo cuja largura está mais próxima de 1080,
    desde que a altura seja maior que a largura (vertical real).
    """
    verticais = [
        a for a in arquivos
        if a.get("width") and a.get("height") and a["height"] > a["width"]
    ]
    if not verticais:
        # fallback: aceita qualquer um e a normalização do ffmpeg cuida.
        verticais = [a for a in arquivos if a.get("width")]
    if not verticais:
        return None

    verticais.sort(key=lambda a: abs(a["width"] - 1080))
    return verticais[0]


def baixar_video(url: str, caminho_saida: Path) -> Path:
    """
    Baixa o arquivo apontado por `url` para `caminho_saida` usando streaming
    em chunks de 1MB (evita estourar memória em arquivos grandes).
    """
    caminho_saida.parent.mkdir(parents=True, exist_ok=True)

    with requests.get(url, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        with open(caminho_saida, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

    if caminho_saida.stat().st_size == 0:
        raise RuntimeError(f"Download vazio: {url}")

    return caminho_saida


def buscar_e_baixar_cenas(
    cenas: list[dict], pasta_saida: Path
) -> list[dict]:
    """
    Para cada cena, faz busca + download e enriquece o dict com:
      - caminho_arquivo: Path do MP4 baixado
      - metadados de atribuição (fotografo_nome, fotografo_url, pexels_url)

    Se a query principal falhar, tenta uma versão simplificada
    (só a primeira palavra) antes de desistir.

    Cenas sem vídeo encontrado recebem caminho_arquivo=None — o orquestrador
    decide se aborta ou faz fallback.
    """
    pasta_saida.mkdir(parents=True, exist_ok=True)
    resultado: list[dict] = []

    for cena in cenas:
        query = cena.get("query_pexels", "").strip()
        if not query:
            cena_enriq = dict(cena, caminho_arquivo=None)
            resultado.append(cena_enriq)
            continue

        print(f"  [pexels] cena {cena.get('ordem')}: '{query}'")
        match = buscar_video(query)

        # Fallback: tenta primeira palavra apenas.
        if match is None:
            primeira = query.split()[0]
            if primeira and primeira.lower() != query.lower():
                print(f"  [pexels] fallback: '{primeira}'")
                match = buscar_video(primeira)

        if match is None:
            print(f"  [pexels] nenhum vídeo encontrado para cena {cena.get('ordem')}")
            cena_enriq = dict(cena, caminho_arquivo=None)
            resultado.append(cena_enriq)
            continue

        nome_arquivo = f"cena_{cena.get('ordem', 0):02d}_{match['id_pexels']}.mp4"
        caminho = pasta_saida / nome_arquivo
        baixar_video(match["url_download"], caminho)

        cena_enriq = dict(cena)
        cena_enriq["caminho_arquivo"] = caminho
        cena_enriq["pexels_id"] = match["id_pexels"]
        cena_enriq["pexels_url"] = match["pexels_url"]
        cena_enriq["fotografo_nome"] = match["fotografo_nome"]
        cena_enriq["fotografo_url"] = match["fotografo_url"]
        cena_enriq["video_duracao"] = match["duracao"]
        cena_enriq["video_largura"] = match["largura"]
        cena_enriq["video_altura"] = match["altura"]
        resultado.append(cena_enriq)

    return resultado


# =========================================================================
# Teste rápido isolado
# =========================================================================
if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    print("Testando busca por 'desert sunset silhouette'...")
    match = buscar_video("desert sunset silhouette")
    if match is None:
        print("Nada encontrado.")
    else:
        print("Encontrado:")
        for k, v in match.items():
            print(f"  {k}: {v}")

        saida = Path("/tmp/teste_pexels.mp4")
        print(f"Baixando para {saida}...")
        baixar_video(match["url_download"], saida)
        print(f"OK. Tamanho: {saida.stat().st_size / 1024:.1f} KB")
