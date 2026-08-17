"""Interface pública do módulo `pipeline`.

A feature `videos` consome APENAS daqui.
"""

from src.pipeline.domain.entities import (
    Cena,
    CenaComStock,
    Narracao,
    OverlayLegenda,
    PalavraTranscrita,
    Post,
    ResultadoPipeline,
    Roteiro,
)
from src.pipeline.domain.protocols import (
    RoteiroGeneratorProtocol,
    StockVideoProtocol,
    StorageProtocol,
    TranscriptionProtocol,
    TtsProviderProtocol,
    VideoComposerProtocol,
)
from src.pipeline.orchestrator import (
    ETAPAS,
    CallbackProgresso,
    EntradaPipeline,
    PipelineOrchestrator,
)

__all__ = [
    "Cena",
    "CenaComStock",
    "CallbackProgresso",
    "ETAPAS",
    "EntradaPipeline",
    "Narracao",
    "OverlayLegenda",
    "PalavraTranscrita",
    "PipelineOrchestrator",
    "Post",
    "ResultadoPipeline",
    "Roteiro",
    "RoteiroGeneratorProtocol",
    "StockVideoProtocol",
    "StorageProtocol",
    "TranscriptionProtocol",
    "TtsProviderProtocol",
    "VideoComposerProtocol",
]
