"""Adapter para composição final via FFmpeg.

Delega ao `legacy/video.py` (montar_video). Acrescenta geração de
thumbnail via ffmpeg direto (não havia no legacy).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from legacy.video import montar_video as _montar_video
from src.pipeline.domain.entities import CenaComStock, OverlayLegenda


class FfmpegVideoComposer:
    def compor(
        self,
        *,
        cenas: list[CenaComStock],
        audio_narracao: Path,
        overlays: list[OverlayLegenda],
        musica_fundo: Path | None,
        caminho_saida: Path,
    ) -> Path:
        cenas_dicts = [
            {
                "ordem": c.cena.ordem,
                "trecho_texto": c.cena.trecho_texto,
                "query_pexels": c.cena.query_pexels,
                "caminho_arquivo": c.caminho_arquivo,
            }
            for c in cenas
        ]
        overlays_dicts = [
            {"png": o.png, "inicio": o.inicio, "fim": o.fim, "texto": o.texto}
            for o in overlays
        ]
        return _montar_video(
            cenas=cenas_dicts,
            audio_narracao=audio_narracao,
            overlays_legenda=overlays_dicts,
            musica_fundo=musica_fundo,
            caminho_saida=caminho_saida,
        )

    def gerar_thumbnail(
        self,
        *,
        caminho_video: Path,
        caminho_saida: Path,
        instante_segundos: float = 1.5,
        largura: int = 405,
    ) -> Path:
        """Extrai um frame e salva como JPEG vertical (default ~400x711)."""
        if shutil.which("ffmpeg") is None:
            raise RuntimeError("ffmpeg não encontrado no PATH")

        caminho_saida.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-ss", f"{instante_segundos:.2f}",
            "-i", str(caminho_video),
            "-vframes", "1",
            "-vf", f"scale={largura}:-1",
            "-q:v", "3",
            str(caminho_saida),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"FFmpeg falhou ao gerar thumbnail: {proc.stderr}")
        return caminho_saida
