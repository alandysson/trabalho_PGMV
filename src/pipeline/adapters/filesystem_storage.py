"""Storage local em filesystem.

Estrutura criada em runtime:

    storage/
    ├── videos/{job_id}.mp4
    ├── thumbnails/{job_id}.jpg
    └── jobs/{job_id}/        # temporários durante geração
"""

from __future__ import annotations

import secrets
from pathlib import Path


class FilesystemStorage:
    def __init__(
        self,
        raiz: Path,
        pasta_musicas: Path | None = None,
    ) -> None:
        self._raiz = Path(raiz)
        self._raiz.mkdir(parents=True, exist_ok=True)
        (self._raiz / "videos").mkdir(exist_ok=True)
        (self._raiz / "thumbnails").mkdir(exist_ok=True)
        (self._raiz / "jobs").mkdir(exist_ok=True)
        self._pasta_musicas = pasta_musicas

    def pasta_de_job(self, job_id: str) -> Path:
        pasta = self._raiz / "jobs" / job_id
        pasta.mkdir(parents=True, exist_ok=True)
        return pasta

    def caminho_video_final(self, job_id: str) -> Path:
        return self._raiz / "videos" / f"{job_id}.mp4"

    def caminho_thumbnail(self, job_id: str) -> Path:
        return self._raiz / "thumbnails" / f"{job_id}.jpg"

    def musica_aleatoria(self) -> Path | None:
        """Sorteia uma trilha de `assets/music/*.mp3`. None se pasta vazia."""
        if self._pasta_musicas is None or not self._pasta_musicas.exists():
            return None
        candidatos = sorted(self._pasta_musicas.glob("*.mp3"))
        if not candidatos:
            return None
        return candidatos[secrets.randbelow(len(candidatos))]
