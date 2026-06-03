from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_login
from app.models import Assento, Onibus
from app.services import ocupacao
from app.templating import templates

router = APIRouter(prefix="/onibus")


def _parse_data(data: str | None) -> date:
    if not data:
        return date.today()
    try:
        return datetime.strptime(data, "%Y-%m-%d").date()
    except ValueError:
        return date.today()


@router.get("/{onibus_id}")
def ver_mapa(
    onibus_id: int,
    request: Request,
    data: str | None = None,
    usuario: dict = Depends(require_login),
    db: Session = Depends(get_db),
):
    onibus = db.get(Onibus, onibus_id)
    if not onibus:
        raise HTTPException(status_code=404, detail="Ônibus não encontrado")

    dia = _parse_data(data)
    mapa = ocupacao.montar_mapa(db, onibus, dia)

    return templates.TemplateResponse(
        "onibus_mapa.html",
        {"request": request, "mapa": mapa, "data": dia.isoformat(), "usuario": usuario},
    )


@router.get("/{onibus_id}/assento/{assento_id}")
def detalhe_assento(
    onibus_id: int,
    assento_id: int,
    request: Request,
    data: str | None = None,
    usuario: dict = Depends(require_login),
    db: Session = Depends(get_db),
):
    """Partial HTMX: dados do assento/colaborador no modal."""
    onibus = db.get(Onibus, onibus_id)
    assento = db.get(Assento, assento_id)
    if not onibus or not assento or assento.onibus_id != onibus_id:
        raise HTTPException(status_code=404, detail="Assento não encontrado")

    dia = _parse_data(data)
    mapa = ocupacao.montar_mapa(db, onibus, dia)
    view = next((a for a in mapa.assentos if a.id == assento_id), None)

    return templates.TemplateResponse(
        "partials/seat_detail.html",
        {"request": request, "onibus": onibus, "assento": view, "data": dia.isoformat()},
    )
