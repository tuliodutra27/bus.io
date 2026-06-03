"""Cálculo de ocupação de um ônibus em uma data.

Regra do modelo híbrido:

    ocupação(ônibus, data) = AlocacaoFixa(turno_letra)
                             − ausências(data)
                             + extras(data: hora_extra / eventual)

Para ônibus administrativos, turno_letra='ADM'.
Para ônibus de turno, turno_letra é a letra do ciclo ativo (A/B/C/D).
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models import (
    Assento,
    AlocacaoFixa,
    Colaborador,
    ExcecaoData,
    Onibus,
    TipoExcecao,
    TipoOnibus,
    LETRA_ADM,
)


@dataclass
class AssentoView:
    id: int
    numero: int
    fila: int
    coluna: int
    lado: str
    status: str = "livre"           # "livre" | "ocupado"
    origem: Optional[str] = None    # "fixo" | "hora_extra" | "eventual"
    colaborador: Optional[dict] = None


@dataclass
class MapaView:
    onibus: Onibus
    assentos: list[AssentoView] = field(default_factory=list)
    total: int = 0
    ocupados: int = 0
    turno_letra: Optional[str] = None   # letra ativa exibida no mapa (turno buses)

    @property
    def livres(self) -> int:
        return self.total - self.ocupados

    @property
    def filas(self) -> list[int]:
        return sorted({a.fila for a in self.assentos})


def _colaborador_dict(colab: Colaborador) -> dict:
    return {
        "id": colab.id,
        "nome": colab.nome,
        "matricula": colab.matricula,
        "setor": colab.setor,
        "telefone": colab.telefone,
        "regime": colab.regime.value if colab.regime else None,
        "cidade": colab.cidade,
        "bairro": colab.bairro,
    }


def montar_mapa(
    db: Session,
    onibus: Onibus,
    dia: date,
    turno_letra: Optional[str] = None,
) -> MapaView:
    """Monta o mapa de assentos do ônibus para a data informada.

    Para ônibus administrativos, usa turno_letra='ADM' (ignora o parâmetro).
    Para ônibus de turno, usa o turno_letra recebido (obrigatório).
    """
    # Determina o filtro de letra para o roster fixo
    if onibus.tipo == TipoOnibus.admin:
        letra_filtro = LETRA_ADM
    else:
        letra_filtro = turno_letra or LETRA_ADM  # fallback para evitar erro

    assentos = (
        db.query(Assento)
        .filter(Assento.onibus_id == onibus.id)
        .order_by(Assento.numero)
        .all()
    )

    # Roster fixo filtrado pela letra do turno
    fixos = {
        a.assento_id: a.colaborador
        for a in db.query(AlocacaoFixa)
        .join(Assento)
        .filter(
            Assento.onibus_id == onibus.id,
            AlocacaoFixa.turno_letra == letra_filtro,
        )
        .all()
    }

    # Exceções do dia (independentes de turno_letra)
    excecoes = (
        db.query(ExcecaoData)
        .join(Assento)
        .filter(Assento.onibus_id == onibus.id, ExcecaoData.data == dia)
        .all()
    )
    ausencias = {e.assento_id for e in excecoes if e.tipo == TipoExcecao.ausencia}
    extras = {
        e.assento_id: e
        for e in excecoes
        if e.tipo in (TipoExcecao.hora_extra, TipoExcecao.eventual)
    }

    views: list[AssentoView] = []
    ocupados = 0
    for a in assentos:
        view = AssentoView(
            id=a.id, numero=a.numero, fila=a.fila, coluna=a.coluna, lado=a.lado
        )

        colab_fixo = fixos.get(a.id)
        if colab_fixo and a.id not in ausencias:
            view.status = "ocupado"
            view.origem = "fixo"
            view.colaborador = _colaborador_dict(colab_fixo)

        # Extra tem precedência de exibição no dia
        extra = extras.get(a.id)
        if extra and extra.colaborador:
            view.status = "ocupado"
            view.origem = extra.tipo.value
            view.colaborador = _colaborador_dict(extra.colaborador)

        if view.status == "ocupado":
            ocupados += 1
        views.append(view)

    return MapaView(
        onibus=onibus,
        assentos=views,
        total=len(views),
        ocupados=ocupados,
        turno_letra=letra_filtro if onibus.tipo == TipoOnibus.micro else None,
    )


def onibus_turno_da_rota(db: Session, rota_id: int) -> Optional[Onibus]:
    """Retorna o ônibus de turno (micro) que atende a rota informada."""
    if not rota_id:
        return None
    return (
        db.query(Onibus)
        .filter(Onibus.rota_id == rota_id, Onibus.tipo == TipoOnibus.micro)
        .first()
    )


def get_letra_ativa(db: Session) -> str:
    """Retorna a letra do ciclo de turno atualmente ativa (padrão 'A')."""
    from app.models import Configuracao
    config = db.get(Configuracao, "turno_letra_ativa")
    return config.valor if config else "A"
