from datetime import date, datetime

from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_login, require_logistica
from app.models import (
    Colaborador,
    ExcecaoData,
    Regime,
    SolicitacaoHoraExtra,
    StatusSolicitacao,
    TipoExcecao,
)
from app.services import ocupacao
from app.templating import templates

router = APIRouter(prefix="/hora-extra")


def _parse_data(data: str | None) -> date:
    if not data:
        return date.today()
    try:
        return datetime.strptime(data, "%Y-%m-%d").date()
    except ValueError:
        return date.today()


@router.get("")
def form(
    request: Request,
    usuario: dict = Depends(require_login),
    db: Session = Depends(get_db),
):
    colaboradores = (
        db.query(Colaborador)
        .filter(Colaborador.regime == Regime.admin)
        .order_by(Colaborador.nome)
        .all()
    )
    return templates.TemplateResponse(
        "hora_extra.html",
        {
            "request": request,
            "colaboradores": colaboradores,
            "hoje": date.today().isoformat(),
            "usuario": usuario,
        },
    )


@router.get("/sugestao")
def sugestao(
    request: Request,
    colaborador_id: int,
    data: str | None = None,
    usuario: dict = Depends(require_login),
    db: Session = Depends(get_db),
):
    """Sugere o ônibus de turno da rota do solicitante e mostra o mapa."""
    dia = _parse_data(data)
    colaborador = db.get(Colaborador, colaborador_id)
    onibus_turno = (
        ocupacao.onibus_turno_da_rota(db, colaborador.rota_id) if colaborador else None
    )

    # Para o mapa de hora extra, mostra todos os assentos disponíveis na data
    # independentemente do ciclo de turno (qualquer assento livre é marcável)
    letra_ativa = ocupacao.get_letra_ativa(db)
    mapa = ocupacao.montar_mapa(db, onibus_turno, dia, turno_letra=letra_ativa) if onibus_turno else None

    modo_mapa = "view" if usuario["role"] == "viewer" else "marcar"

    return templates.TemplateResponse(
        "partials/hora_extra_resultado.html",
        {
            "request": request,
            "colaborador": colaborador,
            "onibus": onibus_turno,
            "mapa": mapa,
            "data": dia.isoformat(),
            "modo_mapa": modo_mapa,
            "erro": None if onibus_turno else "Nenhum ônibus de turno funcional encontrado para a rota deste colaborador.",
        },
    )


@router.post("/marcar")
def marcar(
    request: Request,
    colaborador_id: int = Form(...),
    assento_id: int = Form(...),
    data: str = Form(...),
    usuario: dict = Depends(require_logistica),
    db: Session = Depends(get_db),
):
    """Marca o assento do solicitante no ônibus de turno para a data."""
    dia = _parse_data(data)
    colaborador = db.get(Colaborador, colaborador_id)
    onibus_turno = ocupacao.onibus_turno_da_rota(db, colaborador.rota_id)
    letra_ativa = ocupacao.get_letra_ativa(db)

    mapa = ocupacao.montar_mapa(db, onibus_turno, dia, turno_letra=letra_ativa)
    alvo = next((a for a in mapa.assentos if a.id == assento_id), None)

    mensagem = None
    if alvo is None:
        mensagem = "Assento inválido."
    elif alvo.status == "ocupado":
        mensagem = f"Assento {alvo.numero} já está ocupado nesta data."
    else:
        db.add(
            ExcecaoData(
                data=dia,
                assento_id=assento_id,
                colaborador_id=colaborador_id,
                tipo=TipoExcecao.hora_extra,
            )
        )
        db.add(
            SolicitacaoHoraExtra(
                colaborador_id=colaborador_id,
                data=dia,
                onibus_turno_id=onibus_turno.id,
                assento_id=assento_id,
                status=StatusSolicitacao.aprovada,
            )
        )
        db.commit()
        mensagem = f"Assento {alvo.numero} marcado para {colaborador.nome}."

    mapa = ocupacao.montar_mapa(db, onibus_turno, dia, turno_letra=letra_ativa)
    return templates.TemplateResponse(
        "partials/hora_extra_resultado.html",
        {
            "request": request,
            "colaborador": colaborador,
            "onibus": onibus_turno,
            "mapa": mapa,
            "data": dia.isoformat(),
            "modo_mapa": "marcar",
            "mensagem": mensagem,
            "erro": None,
        },
    )
