"""Orquestrador do pipeline de geração de vídeos.

Coordena as 5 etapas — roteiro → narração → transcrição → busca stock →
composição — usando APENAS Protocols. Trocar qualquer adapter (TTS,
LLM, stock) = mudar uma linha no container.

Reporta progresso por callback (não conhece o `Job` da feature `videos`
— DIP).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from src.pipeline.domain.entities import ResultadoPipeline
from src.pipeline.domain.protocols import (
    RoteiroGeneratorProtocol,
    StockVideoProtocol,
    StorageProtocol,
    TranscriptionProtocol,
    TtsProviderProtocol,
    VideoComposerProtocol,
)
from src.temas import BaseTemaProvider, HistoriaEscolhida


# Etapas reportadas pelo callback (alinhadas com spec_backend.md).
ETAPAS = [
    ("escolha_historia", 5),
    ("roteiro", 15),
    ("narracao", 30),
    ("transcricao", 45),
    ("buscando_videos_pexels", 60),
    ("compondo_video", 85),
    ("finalizado", 100),
]


@dataclass
class EntradaPipeline:
    job_id: str
    provider_tema: BaseTemaProvider
    historia: HistoriaEscolhida
    voz_tts: str | None = None
    num_cenas: int = 6


CallbackProgresso = Callable[[str, int], None]


class PipelineOrchestrator:
    def __init__(
        self,
        roteiro_gen: RoteiroGeneratorProtocol,
        tts: TtsProviderProtocol,
        transcription: TranscriptionProtocol,
        stock: StockVideoProtocol,
        composer: VideoComposerProtocol,
        storage: StorageProtocol,
    ) -> None:
        self._roteiro_gen = roteiro_gen
        self._tts = tts
        self._transcription = transcription
        self._stock = stock
        self._composer = composer
        self._storage = storage

    def executar(
        self,
        entrada: EntradaPipeline,
        callback: CallbackProgresso | None = None,
    ) -> ResultadoPipeline:
        _cb = callback or (lambda *_: None)
        prov = entrada.provider_tema
        h = entrada.historia
        pasta = self._storage.pasta_de_job(entrada.job_id)

        # 1. (História já escolhida antes do pipeline pelo VideosService)
        _cb("escolha_historia", 5)

        # 2. Roteiro
        _cb("roteiro", 15)
        roteiro = self._roteiro_gen.gerar_roteiro(
            titulo=h.titulo,
            referencia=h.referencia,
            personagens=h.personagens,
            tema_central=h.tema_central,
            system_prompt=prov.system_prompt_roteiro(),
        )

        # 3. Narração
        _cb("narracao", 30)
        narracao = self._tts.gerar(
            texto=roteiro.texto,
            caminho_saida=pasta / "narracao.mp3",
            voz=entrada.voz_tts,
        )

        # 4. Transcrição
        _cb("transcricao", 45)
        palavras = self._transcription.transcrever(caminho_audio=narracao.caminho_audio)
        overlays = self._transcription.gerar_overlays_legenda(
            palavras=palavras,
            pasta_saida=pasta / "legendas",
        )

        # 5. Cenas + busca/download Pexels
        _cb("buscando_videos_pexels", 60)
        rest = prov.restricoes_visuais()
        dicas = self._formatar_dicas(rest.periodo, rest.paleta, rest.ambientacao, rest.palavras_chave_extras)
        cenas = self._roteiro_gen.gerar_cenas(
            roteiro=roteiro.texto,
            num_cenas=entrada.num_cenas,
            dicas_visuais=dicas,
        )
        cenas_com_stock = self._stock.buscar_e_baixar(
            cenas=cenas,
            pasta_saida=pasta / "stock",
        )

        # 6. Composição
        _cb("compondo_video", 85)
        caminho_video = self._storage.caminho_video_final(entrada.job_id)
        self._composer.compor(
            cenas=cenas_com_stock,
            audio_narracao=narracao.caminho_audio,
            overlays=overlays,
            musica_fundo=self._storage.musica_aleatoria(),
            caminho_saida=caminho_video,
        )
        caminho_thumb = self._storage.caminho_thumbnail(entrada.job_id)
        try:
            self._composer.gerar_thumbnail(
                caminho_video=caminho_video, caminho_saida=caminho_thumb
            )
        except Exception:
            caminho_thumb = None  # type: ignore[assignment]

        # 7. Legenda + hashtags pra publicação (1 chamada Haiku, ~1-2s)
        post = self._roteiro_gen.gerar_post(
            titulo=roteiro.titulo,
            referencia=h.referencia,
            tema_central=h.tema_central,
            tema_nome=prov.nome_exibicao,
            roteiro=roteiro.texto,
        )

        _cb("finalizado", 100)

        return ResultadoPipeline(
            titulo=roteiro.titulo,
            subtitulo=h.referencia,
            roteiro=roteiro.texto,
            caminho_video=caminho_video,
            caminho_thumbnail=caminho_thumb,
            duracao_segundos=narracao.duracao_segundos,
            tamanho_bytes=caminho_video.stat().st_size,
            post=post,
            creditos=[
                {
                    "fotografo_nome": c.fotografo_nome,
                    "fotografo_url": c.fotografo_url,
                    "pexels_url": c.pexels_url,
                }
                for c in cenas_com_stock
                if c.fotografo_nome
            ],
        )

    @staticmethod
    def _formatar_dicas(periodo: str, paleta: str, ambientacao: str, extras: list[str]) -> str:
        partes = []
        if periodo:
            partes.append(f"Período: {periodo}")
        if paleta:
            partes.append(f"Paleta: {paleta}")
        if ambientacao:
            partes.append(f"Ambientação: {ambientacao}")
        if extras:
            partes.append(f"Palavras-chave extras: {', '.join(extras)}")
        return " | ".join(partes)
