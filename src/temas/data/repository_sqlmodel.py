"""Implementação SQLModel do cache de sugestões."""

from __future__ import annotations

import json

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from src.temas.domain.entities import HistoriaEscolhida
from src.temas.domain.models import HistoriaSugerida


class HistoriaSugeridaRepositorySqlModel:
    def __init__(self, session: Session) -> None:
        self._session = session

    def salvar(self, tema_id: str, historia: HistoriaEscolhida) -> None:
        registro = HistoriaSugerida(
            tema_id=tema_id,
            historia_id_estavel=historia.id,
            titulo=historia.titulo,
            referencia=historia.referencia,
            personagens_json=json.dumps(historia.personagens, ensure_ascii=False),
            tema_central=historia.tema_central,
        )
        self._session.add(registro)
        try:
            self._session.commit()
        except IntegrityError:
            # IDs colidem só se Claude inventar o mesmo snake_case duas vezes.
            # Não é erro fatal — só ignoramos a duplicata e seguimos.
            self._session.rollback()

    def listar_por_tema(self, tema_id: str) -> list[HistoriaEscolhida]:
        stmt = select(HistoriaSugerida).where(HistoriaSugerida.tema_id == tema_id)
        registros = self._session.exec(stmt).all()
        return [
            HistoriaEscolhida(
                id=r.historia_id_estavel,
                titulo=r.titulo,
                referencia=r.referencia,
                personagens=json.loads(r.personagens_json) if r.personagens_json else [],
                tema_central=r.tema_central,
            )
            for r in registros
        ]
