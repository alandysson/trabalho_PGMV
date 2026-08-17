"""Entidades de domínio da feature `videos`."""

from __future__ import annotations

from enum import Enum


class StatusJob(str, Enum):
    PENDENTE = "pendente"
    PROCESSANDO = "processando"
    CONCLUIDO = "concluido"
    FALHOU = "falhou"


# Etapas reconhecidas — espelham ETAPAS do `src/pipeline/orchestrator.py`.
ETAPAS_VALIDAS = {
    "escolha_historia",
    "roteiro",
    "narracao",
    "transcricao",
    "buscando_videos_pexels",
    "compondo_video",
    "finalizado",
}
