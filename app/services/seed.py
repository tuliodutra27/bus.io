"""Popula o banco com dados de exemplo.

MVP: 2 ônibus 100% funcionais (1 administrativo + 1 de turno na mesma rota,
para viabilizar o fluxo de hora extra) e os demais apenas para exibição.
"""

from sqlalchemy.orm import Session

from app.models import (
    AlocacaoFixa,
    Assento,
    Colaborador,
    Onibus,
    Regime,
    Rota,
    TipoOnibus,
)

CAMPOS = "Campos dos Goytacazes"
SJB = "São João da Barra"


def _gerar_assentos(onibus: Onibus) -> None:
    """Cria os assentos no layout 2 + corredor + 2 (colunas 1,2 | 3,4)."""
    for n in range(1, onibus.capacidade + 1):
        fila = (n - 1) // 4 + 1
        coluna = (n - 1) % 4 + 1
        lado = "esq" if coluna in (1, 2) else "dir"
        onibus.assentos.append(
            Assento(numero=n, fila=fila, coluna=coluna, lado=lado)
        )


# Colaboradores fixos do ônibus ADMINISTRATIVO funcional (ADM-01 / rota Campos-Centro)
COLAB_ADMIN = [
    ("Ana Paula Ferreira", "ADM1001", "Financeiro", "Centro", 3),
    ("Bruno Carvalho Lima", "ADM1002", "RH", "Parque Tamandaré", 4),
    ("Carla Souza Mendes", "ADM1003", "Compras", "Pelinca", 7),
    ("Diego Nascimento", "ADM1004", "TI", "Jardim Carioca", 8),
    ("Eduarda Ramos", "ADM1005", "Jurídico", "Centro", 11),
    ("Felipe Antunes", "ADM1006", "Engenharia", "Flamboyant", 12),
    ("Gabriela Pinto", "ADM1007", "SSMA", "Caju", 15),
    ("Henrique Barbosa", "ADM1008", "Financeiro", "Centro", 16),
    ("Isabela Cardoso", "ADM1009", "Suprimentos", "Pelinca", 19),
    ("João VitorTeixeira", "ADM1010", "Engenharia", "Parque Califórnia", 20),
    ("Larissa Moreira", "ADM1011", "RH", "Turf Club", 23),
    ("Marcelo Drummond", "ADM1012", "Planejamento", "Centro", 24),
]

# Colaboradores fixos do ônibus de TURNO funcional (TUR-01 / mesma rota)
COLAB_TURNO = [
    ("Nícolas Pereira", "TUR2001", "Operação", "Centro", 2),
    ("Olívia Santana", "TUR2002", "Operação", "Pelinca", 5),
    ("Paulo Roberto Dias", "TUR2003", "Manutenção", "Jardim Carioca", 6),
    ("Quésia Almeida", "TUR2004", "Operação", "Flamboyant", 9),
    ("Rafael Monteiro", "TUR2005", "Manutenção", "Caju", 10),
    ("Sabrina Lopes", "TUR2006", "Operação", "Centro", 13),
    ("Thiago Fontes", "TUR2007", "Logística", "Parque Califórnia", 14),
]


def seed(db: Session) -> None:
    if db.query(Onibus).count() > 0:
        return  # já populado

    # --- Rota principal (Campos) que terá os 2 ônibus funcionais ---
    rota_campos = Rota(
        nome="Campos – Centro / Porto do Açu",
        cidade=CAMPOS,
        bairros="Centro; Pelinca; Parque Tamandaré; Jardim Carioca; Flamboyant; Caju; Parque Califórnia; Turf Club",
        horarios="Admin 07h-17h | Turno 07h-19h / 19h-07h",
    )
    db.add(rota_campos)
    db.flush()

    # Ônibus 1: administrativo funcional (50 lugares)
    adm01 = Onibus(
        identificador="ADM-01", tipo=TipoOnibus.admin, capacidade=50,
        rota_id=rota_campos.id, ativo=True, exemplo=False,
    )
    _gerar_assentos(adm01)
    db.add(adm01)

    # Ônibus 2: turno funcional (30 lugares), mesma rota -> viabiliza hora extra
    tur01 = Onibus(
        identificador="TUR-01", tipo=TipoOnibus.micro, capacidade=30,
        rota_id=rota_campos.id, ativo=True, exemplo=False,
    )
    _gerar_assentos(tur01)
    db.add(tur01)
    db.flush()

    # --- Colaboradores + alocação fixa nos 2 ônibus funcionais ---
    def _aloca(lista, regime, onibus):
        mapa_assentos = {a.numero: a for a in onibus.assentos}
        for nome, matricula, setor, bairro, num_assento in lista:
            colab = Colaborador(
                nome=nome, matricula=matricula, setor=setor,
                telefone="(22) 99999-0000", regime=regime, cidade=CAMPOS,
                bairro=bairro, rota_id=rota_campos.id,
            )
            db.add(colab)
            db.flush()
            assento = mapa_assentos[num_assento]
            db.add(AlocacaoFixa(assento_id=assento.id, colaborador_id=colab.id))

    _aloca(COLAB_ADMIN, Regime.admin, adm01)
    _aloca(COLAB_TURNO, Regime.turno, tur01)

    # --- Ônibus de exemplo (apenas exibição no MVP) ---
    exemplos = [
        ("Campos – Norte", CAMPOS, "ADM-02", TipoOnibus.admin, 50),
        ("Campos – Sul", CAMPOS, "ADM-03", TipoOnibus.admin, 50),
        ("São João – Centro", SJB, "ADM-04", TipoOnibus.admin, 50),
        ("São João – Atafona", SJB, "ADM-05", TipoOnibus.admin, 50),
        ("Campos – Norte", CAMPOS, "TUR-02", TipoOnibus.micro, 30),
        ("São João – Centro", SJB, "TUR-03", TipoOnibus.micro, 30),
        ("São João – Grussaí", SJB, "TUR-04", TipoOnibus.micro, 30),
    ]
    for nome_rota, cidade, ident, tipo, cap in exemplos:
        rota = Rota(nome=f"{nome_rota} / Porto do Açu", cidade=cidade)
        db.add(rota)
        db.flush()
        onibus = Onibus(
            identificador=ident, tipo=tipo, capacidade=cap,
            rota_id=rota.id, ativo=True, exemplo=True,
        )
        _gerar_assentos(onibus)
        db.add(onibus)

    db.commit()
    print("[seed] dados de exemplo criados.")
