"""Interface pública do módulo de autenticação.

Outros módulos devem importar APENAS daqui:

    from src.auth import AuthService, Usuario, construir_usuario_atual
"""

from src.auth.dependencies import construir_usuario_atual
from src.auth.domain.models import Usuario
from src.auth.routes import criar_router
from src.auth.service import AuthService

__all__ = ["AuthService", "Usuario", "construir_usuario_atual", "criar_router"]
