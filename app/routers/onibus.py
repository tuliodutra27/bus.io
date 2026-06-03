from datetime import date, datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_login, require_logistica
from app.models import Assento, Configuracao, Onibus, TipoOnibus, LETRAS_TURNO
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


def _letra_para_mapa(onibus: Onibus, db: Session, letra_param: str | None) -> str | None:
    """Determina a letra de turno a usar no mapa. None para ônibus admin."""
    if onibus.tipo == TipoOnibus.admin:
        return None
    # Prioridade: parâmetro da URL > configuração global
    if letra_param and letra_param.upper() in LETRAS_TURNO:
        return letra_param.upper()
    return ocupacao.get_letra_ativa(db)


@router.get("/{onibus_id}")
def ver_mapa(
    onibus_id: int,
    request: Request,
    data: str | None = None,
    letra: str | None = None,
    usuario: dict = Depends(require_login),
    db: Session = Depends(get_db),
):
    onibus = db.get(Onibus, onibus_id)
    if not onibus:
        raise HTTPException(status_code=404, detail="Ônibus não encontrado")

    dia = _parse_data(data)
    turno_letra = _letra_para_mapa(onibus, db, letra)
    mapa = ocupacao.montar_mapa(db, onibus, dia, turno_letra=turno_letra)
    letra_ativa = ocupacao.get_letra_ativa(db)

    return templates.TemplateResponse(
        "onibus_mapa.html",
        {
            "request": request,
            "mapa": mapa,
            "data": dia.isoformat(),
            "usuario": usuario,
            "letras_turno": LETRAS_TURNO,
            "letra_ativa": letra_ativa,
        },
    )


@router.get("/{onibus_id}/mapa-parcial")
def mapa_parcial(
    onibus_id: int,
    request: Request,
    data: str | None = None,
    letra: str | None = None,
    usuario: dict = Depends(require_login),
    db: Session = Depends(get_db),
):
    """Partial HTMX: mapa de assentos para exibição no modal do dashboard."""
    onibus = db.get(Onibus, onibus_id)
    if not onibus:
        raise HTTPException(status_code=404, detail="Ônibus não encontrado")

    dia = _parse_data(data)
    turno_letra = _letra_para_mapa(onibus, db, letra)
    mapa = ocupacao.montar_mapa(db, onibus, dia, turno_letra=turno_letra)
    letra_ativa = ocupacao.get_letra_ativa(db)

    return templates.TemplateResponse(
        "partials/onibus_mapa_parcial.html",
        {
            "request": request,
            "mapa": mapa,
            "data": dia.isoformat(),
            "usuario": usuario,
            "letras_turno": LETRAS_TURNO,
            "letra_ativa": letra_ativa,
        },
    )


@router.get("/{onibus_id}/assento/{assento_id}")
def detalhe_assento(
    onibus_id: int,
    assento_id: int,
    request: Request,
    data: str | None = None,
    letra: str | None = None,
    usuario: dict = Depends(require_login),
    db: Session = Depends(get_db),
):
    """Partial HTMX: dados do assento/colaborador no modal."""
    onibus = db.get(Onibus, onibus_id)
    assento = db.get(Assento, assento_id)
    if not onibus or not assento or assento.onibus_id != onibus_id:
        raise HTTPException(status_code=404, detail="Assento não encontrado")

    dia = _parse_data(data)
    turno_letra = _letra_para_mapa(onibus, db, letra)
    mapa = ocupacao.montar_mapa(db, onibus, dia, turno_letra=turno_letra)
    view = next((a for a in mapa.assentos if a.id == assento_id), None)

    return templates.TemplateResponse(
        "partials/seat_detail.html",
        {"request": request, "onibus": onibus, "assento": view, "data": dia.isoformat()},
    )


@router.post("/turno/letra")
def atualizar_letra_ativa(
    request: Request,
    letra: str = Form(...),
    redirect_url: str = Form(default="/"),
    usuario: dict = Depends(require_logistica),
    db: Session = Depends(get_db),
):
    """Atualiza a letra do ciclo de turno ativa globalmente."""
    letra = letra.upper()
    if letra not in LETRAS_TURNO:
        raise HTTPException(status_code=400, detail="Letra inválida")

    config = db.get(Configuracao, "turno_letra_ativa")
    if config:
        config.valor = letra
    else:
        db.add(Configuracao(chave="turno_letra_ativa", valor=letra))
    db.commit()
    return RedirectResponse(redirect_url, status_code=302)
