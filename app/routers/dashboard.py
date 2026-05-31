from datetime import date

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Onibus
from app.services import ocupacao
from app.templating import templates

router = APIRouter()


@router.get("/")
def index(request: Request, db: Session = Depends(get_db)):
    hoje = date.today()
    onibus_list = db.query(Onibus).order_by(Onibus.tipo, Onibus.identificador).all()

    cards = []
    for o in onibus_list:
        mapa = ocupacao.montar_mapa(db, o, hoje)
        cards.append(
            {
                "onibus": o,
                "total": mapa.total,
                "ocupados": mapa.ocupados,
                "livres": mapa.livres,
            }
        )

    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "cards": cards, "hoje": hoje.isoformat()},
    )
