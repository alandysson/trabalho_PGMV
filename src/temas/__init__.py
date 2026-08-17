"""Interface pública do módulo de temas.

Outros módulos (notadamente `pipeline` e `videos`) importam APENAS daqui.
"""

from src.temas.domain.entities import (
    HistoriaEscolhida,
    MetadadosTema,
    RestricoesVisuais,
)
from src.temas.domain.exceptions import CatalogoVazio, TemaNaoEncontrado
from src.temas.domain.provider_protocol import BaseTemaProvider
from src.temas.domain.sugeridor_protocol import (
    ContextoSugestao,
    FalhaSugestao,
    SugeridorHistoriaProtocol,
)
from src.temas.registry import (
    Registry,
    construir_registry,
    ids_disponiveis,
    listar_temas,
    obter_tema,
)
from src.temas.routes import criar_router

__all__ = [
    "BaseTemaProvider",
    "CatalogoVazio",
    "ContextoSugestao",
    "FalhaSugestao",
    "HistoriaEscolhida",
    "MetadadosTema",
    "Registry",
    "RestricoesVisuais",
    "SugeridorHistoriaProtocol",
    "TemaNaoEncontrado",
    "construir_registry",
    "criar_router",
    "ids_disponiveis",
    "listar_temas",
    "obter_tema",
]
