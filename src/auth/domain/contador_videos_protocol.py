"""Interface consumida pela route /auth/eu pra contar vídeos do usuário.

Mora em `auth/domain/` (DIP) — a implementação concreta vive em
`src/videos/data/contador_sqlmodel.py`. Auth não importa de videos.
"""

from __future__ import annotations

from typing import Protocol


class ContadorVideosProtocol(Protocol):
    def contar_concluidos_do_usuario(self, usuario_id: str) -> int: ...
