"""Implementação concreta do `ContadorVideosProtocol` (de `auth/domain/`).

Vive em `videos/data/` porque depende do JobRepository — auth não
importa daqui; é o container que conecta.
"""

from __future__ import annotations

from src.videos.data.repository_protocol import JobRepositoryProtocol


class ContadorVideosViaJobRepo:
    def __init__(self, job_repo: JobRepositoryProtocol) -> None:
        self._repo = job_repo

    def contar_concluidos_do_usuario(self, usuario_id: str) -> int:
        return self._repo.contar_do_usuario(
            usuario_id, apenas_concluidos=True
        )
