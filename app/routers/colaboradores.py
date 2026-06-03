from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_login, require_logistica
from app.models import (
    AlocacaoFixa,
    Assento,
    Colaborador,
    Onibus,
    TipoOnibus,
    LETRA_ADM,
    LETRAS_TURNO,
)
from app.services import ocupacao
from app.templating import templates

router = APIRouter(prefix="/colaboradores")


def _buscar_colaboradores(db: Session, q: str = "", empresa: str = "") -> list:
    query = db.query(Colaborador).order_by(Colaborador.nome)
    if q:
        query = query.filter(Colaborador.nome.ilike(f"%{q}%"))
    if empresa:
        query = query.filter(Colaborador.empresa == empresa)
    return query.all()


def _alocacoes_de(db: Session, colaborador_id: int) -> list:
    return (
        db.query(AlocacaoFixa)
        .join(Assento)
        .filter(AlocacaoFixa.colaborador_id == colaborador_id)
        .all()
    )


def _todos_onibus(db: Session) -> list:
    return (
        db.query(Onibus)
        .filter(Onibus.ativo == True)
        .order_by(Onibus.tipo, Onibus.identificador)
        .all()
    )


def _empresas(db: Session) -> list[str]:
    return [
        e[0]
        for e in db.query(func.distinct(Colaborador.empresa))
        .order_by(Colaborador.empresa)
        .all()
    ]


# ---------------------------------------------------------------------------
# Lista / busca
# ---------------------------------------------------------------------------

@router.get("")
def listar(
    request: Request,
    q: str = "",
    empresa: str = "",
    usuario: dict = Depends(require_login),
    db: Session = Depends(get_db),
):
    return templates.TemplateResponse(
        "colaboradores.html",
        {
            "request": request,
            "colaboradores": _buscar_colaboradores(db, q, empresa),
            "empresas": _empresas(db),
            "q": q,
            "empresa_filtro": empresa,
            "usuario": usuario,
        },
    )


@router.get("/buscar")
def buscar(
    request: Request,
    q: str = "",
    empresa: str = "",
    usuario: dict = Depends(require_login),
    db: Session = Depends(get_db),
):
    """Partial HTMX: retorna apenas as linhas da tabela filtradas."""
    return templates.TemplateResponse(
        "partials/colaboradores_lista.html",
        {
            "request": request,
            "colaboradores": _buscar_colaboradores(db, q, empresa),
            "usuario": usuario,
        },
    )


# ---------------------------------------------------------------------------
# Detalhe + gestão de alocações
# ---------------------------------------------------------------------------

@router.get("/{colaborador_id}")
def detalhe(
    request: Request,
    colaborador_id: int,
    onibus_id: int | None = None,
    letra: str | None = None,
    usuario: dict = Depends(require_login),
    db: Session = Depends(get_db),
):
    colaborador = db.get(Colaborador, colaborador_id)

    onibus_sel = None
    letra_sel = LETRA_ADM
    mapa_novo = None

    if onibus_id:
        onibus_sel = db.get(Onibus, onibus_id)
        if onibus_sel:
            if onibus_sel.tipo == TipoOnibus.admin:
                letra_sel = LETRA_ADM
            elif letra and letra.upper() in LETRAS_TURNO:
                letra_sel = letra.upper()
            else:
                letra_sel = "A"
            mapa_novo = ocupacao.mapa_alocacao_fixa(db, onibus_sel, letra_sel)

    return templates.TemplateResponse(
        "colaborador_detalhe.html",
        {
            "request": request,
            "colaborador": colaborador,
            "alocacoes": _alocacoes_de(db, colaborador_id),
            "todos_onibus": _todos_onibus(db),
            "mapa_novo": mapa_novo,
            "onibus_sel": onibus_sel,
            "letra_sel": letra_sel,
            "letras_turno": LETRAS_TURNO,
            "letra_adm": LETRA_ADM,
            "mensagem": None,
            "erro": None,
            "usuario": usuario,
        },
    )


@router.get("/{colaborador_id}/assentos-livres")
def assentos_livres(
    request: Request,
    colaborador_id: int,
    onibus_id: int,
    letra: str = LETRA_ADM,
    usuario: dict = Depends(require_logistica),
    db: Session = Depends(get_db),
):
    """Partial HTMX: mapa de assentos do roster (sem exceções de data) para alocação."""
    colaborador = db.get(Colaborador, colaborador_id)
    onibus = db.get(Onibus, onibus_id)

    if onibus.tipo == TipoOnibus.admin:
        letra_sel = LETRA_ADM
    elif letra.upper() in LETRAS_TURNO:
        letra_sel = letra.upper()
    else:
        letra_sel = "A"

    mapa = ocupacao.mapa_alocacao_fixa(db, onibus, letra_sel)

    return templates.TemplateResponse(
        "partials/colaborador_mapa_alocar.html",
        {
            "request": request,
            "mapa": mapa,
            "colaborador_id": colaborador_id,
            "colaborador": colaborador,
            "alocar_letra": letra_sel,
            "usuario": usuario,
        },
    )


@router.post("/{colaborador_id}/alocar")
def alocar(
    request: Request,
    colaborador_id: int,
    assento_id: int = Form(...),
    turno_letra: str = Form(LETRA_ADM),
    onibus_id: int = Form(...),
    usuario: dict = Depends(require_logistica),
    db: Session = Depends(get_db),
):
    """Cria uma AlocacaoFixa (assento permanente do roster)."""
    colaborador = db.get(Colaborador, colaborador_id)
    assento = db.get(Assento, assento_id)
    onibus = db.get(Onibus, onibus_id) if onibus_id else (db.get(Onibus, assento.onibus_id) if assento else None)

    mensagem = None
    erro = None

    if not assento or not onibus:
        erro = "Assento inválido."
    else:
        existente = (
            db.query(AlocacaoFixa)
            .filter(
                AlocacaoFixa.assento_id == assento_id,
                AlocacaoFixa.turno_letra == turno_letra,
            )
            .first()
        )
        if existente:
            erro = (
                f"Assento {assento.numero} já está alocado para "
                f"{existente.colaborador.nome} (letra {turno_letra})."
            )
        else:
            db.add(AlocacaoFixa(
                assento_id=assento_id,
                colaborador_id=colaborador_id,
                turno_letra=turno_letra,
            ))
            db.commit()
            mensagem = (
                f"Assento {assento.numero} "
                f"({onibus.identificador}, letra {turno_letra}) "
                f"alocado para {colaborador.nome}."
            )

    # Reconstrói o mapa atualizado para o mesmo ônibus/letra
    mapa_novo = ocupacao.mapa_alocacao_fixa(db, onibus, turno_letra) if onibus else None

    return templates.TemplateResponse(
        "partials/colaborador_alocacoes.html",
        {
            "request": request,
            "colaborador": colaborador,
            "alocacoes": _alocacoes_de(db, colaborador_id),
            "todos_onibus": _todos_onibus(db),
            "mapa_novo": mapa_novo,
            "onibus_sel": onibus,
            "letra_sel": turno_letra,
            "letras_turno": LETRAS_TURNO,
            "letra_adm": LETRA_ADM,
            "mensagem": mensagem,
            "erro": erro,
            "usuario": usuario,
        },
    )


@router.post("/{colaborador_id}/alocacao/{alocacao_id}/remover")
def remover_alocacao(
    request: Request,
    colaborador_id: int,
    alocacao_id: int,
    usuario: dict = Depends(require_logistica),
    db: Session = Depends(get_db),
):
    colaborador = db.get(Colaborador, colaborador_id)
    alocacao = db.get(AlocacaoFixa, alocacao_id)

    mensagem = None
    if alocacao and alocacao.colaborador_id == colaborador_id:
        num = alocacao.assento.numero
        ident = alocacao.assento.onibus.identificador
        db.delete(alocacao)
        db.commit()
        mensagem = f"Alocação do assento {num} ({ident}) removida."

    return templates.TemplateResponse(
        "partials/colaborador_alocacoes.html",
        {
            "request": request,
            "colaborador": colaborador,
            "alocacoes": _alocacoes_de(db, colaborador_id),
            "todos_onibus": _todos_onibus(db),
            "mapa_novo": None,
            "onibus_sel": None,
            "letra_sel": LETRA_ADM,
            "letras_turno": LETRAS_TURNO,
            "letra_adm": LETRA_ADM,
            "mensagem": mensagem,
            "erro": None,
            "usuario": usuario,
        },
    )
