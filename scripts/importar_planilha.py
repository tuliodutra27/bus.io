#!/usr/bin/env python3
"""
importar_planilha.py — Importa dados reais da planilha para o banco bus.io.

Pré-requisito (instalar uma vez):
    pip install openpyxl

Uso:
    python scripts/importar_planilha.py PLANILHA.xlsx [saida.sql]

    Padrão de saída: dados_reais.sql na pasta corrente.

Para aplicar ao banco (com Docker rodando):
    docker exec -i busio_db sh -c \\
        'mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE"' < dados_reais.sql

Observações sobre a planilha:
  - Abas ADM:    01ADM, 02ADM, 03ADM, 04ADM
  - Abas Turno:  ROTA 01Turno, ROTA 02Turno, ROTA 03Turno, ROTA 04Turno
  - 01ADM e ROTA 03Turno/04Turno não têm Nº Assento → só cria Colaborador, sem AlocacaoFixa.
  - Colaboradores que aparecem em múltiplos ônibus são deduplicados pelo nome.
  - Linhas de continuação (mesma pessoa, letras A/B/C/D distintas) são agrupadas.
  - Quant='AFASTADO' → cria Colaborador mas sem AlocacaoFixa.
  - Campo Horario: 'Aliseo ADM'=ALISEO regime admin, 'Aliseo Turno'=ALISEO regime turno,
                   'Tercerizadas'=Terceirizada.
"""

import sys
import unicodedata
from pathlib import Path

try:
    import openpyxl
except ImportError:
    sys.exit("Erro: instale openpyxl antes de rodar o script:\n  pip install openpyxl")


# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

PARES_ROTA = [
    # (num, aba_adm,  aba_turno,        cidade_rota)
    (1, "01ADM",  "ROTA 01Turno", "Campos dos Goytacazes"),
    (2, "02ADM",  "ROTA 02Turno", "Campos dos Goytacazes"),
    (3, "03ADM",  "ROTA 03Turno", "Campos dos Goytacazes"),
    (4, "04ADM",  "ROTA 04Turno", "São João da Barra"),
]

ADM_CAP = 50   # capacidade ônibus administrativo
TUR_CAP = 32   # capacidade micro de turno (margem para ROTA 01Turno que tem 32 vagas)
LETRAS_VALIDAS = {"A", "B", "C", "D"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalizar_nome(txt: str) -> str:
    """Remove acentos, padroniza espaços, converte para maiúsculo."""
    nfkd = unicodedata.normalize("NFKD", str(txt))
    sem_acento = "".join(c for c in nfkd if not unicodedata.combining(c))
    return " ".join(sem_acento.upper().split())


def sql_str(val) -> str:
    if val is None:
        return "NULL"
    return "'" + str(val).replace("\\", "\\\\").replace("'", "\\'") + "'"


def sql_int(val) -> str:
    if val is None:
        return "NULL"
    try:
        return str(int(val))
    except (ValueError, TypeError):
        return "NULL"


def detectar_colunas(header: tuple) -> dict:
    """
    Mapeia nome → índice de coluna pelo cabeçalho.
    Aceita layouts diferentes (ROTA 01Turno tem colunas deslocadas).
    """
    cols = {}
    for i, v in enumerate(header):
        if v is None:
            continue
        k = normalizar_nome(str(v))
        if "NOME" in k and len(k.split()) <= 3:
            cols.setdefault("nome", i)
        elif "ASSENTO" in k and "N" in k:
            cols.setdefault("assento", i)
        elif k in ("CARGO", "FUNCAO"):
            cols.setdefault("cargo", i)
        elif "HORARIO" in k or "TURNO" in k:
            cols.setdefault("horario", i)
        elif "BAIRRO" in k:
            cols.setdefault("bairro", i)
        elif "TELEFONE" in k or "FONE" in k:
            cols.setdefault("telefone", i)
        elif "LETRA" in k:
            cols.setdefault("letra", i)
        elif "MATRICUL" in k:
            cols.setdefault("matricula", i)
        elif "QUANT" in k:
            cols.setdefault("quant", i)
    return cols


def empresa_regime(horario: str) -> tuple[str, str]:
    """Retorna (empresa, regime) a partir do campo Horario/Turno da planilha."""
    if not horario:
        return ("ALISEO", "turno")
    h = str(horario).strip()
    if "Tercerizadas" in h or "Terceirizadas" in h:
        return ("Terceirizada", "turno")
    if "ADM" in h.upper():
        return ("ALISEO", "admin")
    return ("ALISEO", "turno")


def extrair_nome_rota(ws) -> str:
    """Extrai o nome da rota da primeira linha da aba."""
    row1 = next(ws.iter_rows(min_row=1, max_row=1, values_only=True))
    for v in row1:
        if v and str(v).strip():
            return str(v).strip()
    return ws.title


# ---------------------------------------------------------------------------
# Leitura das abas
# ---------------------------------------------------------------------------

def ler_aba_adm(ws) -> list[dict]:
    """
    Lê aba ADM. Retorna lista de dicts por colaborador.
    Header na linha 2, dados a partir da linha 3.
    """
    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 2:
        return []

    cols = detectar_colunas(rows[1])
    if "nome" not in cols:
        print(f"  AVISO: coluna 'Nome' não encontrada em {ws.title}")
        return []

    resultado = []
    for row in rows[2:]:
        nome_val = row[cols["nome"]] if len(row) > cols["nome"] else None
        if not nome_val or str(nome_val).strip() == "":
            continue

        nome = str(nome_val).strip()
        horario_raw = row[cols["horario"]] if "horario" in cols and len(row) > cols["horario"] else None
        emp, reg = empresa_regime(str(horario_raw or "Aliseo ADM"))

        assento_num = None
        if "assento" in cols and len(row) > cols["assento"]:
            av = row[cols["assento"]]
            if av is not None:
                try:
                    assento_num = int(av)
                except (ValueError, TypeError):
                    pass

        cargo = None
        if "cargo" in cols and len(row) > cols["cargo"]:
            cv = row[cols["cargo"]]
            cargo = str(cv).strip() if cv else None

        bairro = None
        if "bairro" in cols and len(row) > cols["bairro"]:
            bv = row[cols["bairro"]]
            bairro = str(bv).strip() if bv else None

        resultado.append({
            "nome": nome,
            "cargo": cargo or None,
            "bairro": bairro or None,
            "telefone": None,
            "empresa": emp,
            "regime": reg,
            "assento": assento_num,
            "letras": ["ADM"],   # ônibus administrativo usa sentinel ADM
        })

    return resultado


def ler_aba_turno(ws) -> list[dict]:
    """
    Lê aba Turno. Lida com:
      - ROTA 01Turno: colunas deslocadas (Matricula em col 3, Nome em col 5)
      - ROTA 02-04: colunas em posições padrão
      - Linhas de continuação (mesma pessoa, letras A/B/C/D adicionais)
      - Quant='AFASTADO' → sem AlocacaoFixa
    """
    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 2:
        return []

    cols = detectar_colunas(rows[1])
    if "nome" not in cols:
        print(f"  AVISO: coluna 'Nome' não encontrada em {ws.title}")
        return []

    c_nome = cols["nome"]
    c_ass  = cols.get("assento")
    c_car  = cols.get("cargo")
    c_bai  = cols.get("bairro")
    c_tel  = cols.get("telefone")
    c_hor  = cols.get("horario")
    c_let  = cols.get("letra")
    c_qua  = cols.get("quant")

    def cel(row, idx):
        if idx is None or idx >= len(row):
            return None
        return row[idx]

    resultado = []
    atual = None  # pessoa sendo acumulada

    for row in rows[2:]:
        nome_val = cel(row, c_nome)
        letra_val = cel(row, c_let)
        quant_val = cel(row, c_qua)

        # Normaliza letra
        letra = None
        if letra_val:
            ls = str(letra_val).strip().upper()
            if ls in LETRAS_VALIDAS:
                letra = ls
            # 'Aliseo ADM' como letra → admin temporário no turno, sem letra

        nome = str(nome_val).strip() if nome_val and str(nome_val).strip() else None

        if nome:
            # Nova pessoa: fecha a anterior e começa nova
            if atual:
                resultado.append(atual)

            afastado = str(quant_val or "").upper() == "AFASTADO"
            horario_raw = cel(row, c_hor)
            emp, reg = empresa_regime(str(horario_raw or "Aliseo Turno"))

            assento_num = None
            av = cel(row, c_ass)
            if av is not None:
                try:
                    assento_num = int(av)
                except (ValueError, TypeError):
                    pass

            cargo = str(cel(row, c_car) or "").strip() or None
            bairro = str(cel(row, c_bai) or "").strip() or None
            tel_raw = cel(row, c_tel)
            telefone = str(tel_raw).strip() if tel_raw else None

            letras = []
            if not afastado and letra:
                letras = [letra]
            # Se Horario é ADM, esta pessoa não tem letra de turno fixa

            atual = {
                "nome": nome,
                "cargo": cargo,
                "bairro": bairro,
                "telefone": telefone,
                "empresa": emp,
                "regime": reg,
                "assento": assento_num,
                "letras": letras,
                "afastado": afastado,
            }

        elif letra and atual and letra not in atual["letras"]:
            # Linha de continuação: mesma pessoa, nova letra
            atual["letras"].append(letra)

    if atual:
        resultado.append(atual)

    return resultado


# ---------------------------------------------------------------------------
# Geração de SQL
# ---------------------------------------------------------------------------

def gerar_assentos_vals(onibus_id: int, capacidade: int, id_inicial: int) -> tuple[list[str], int]:
    """
    Retorna (lista_de_values_sql, próximo_id_livre).
    Cada value: (id, onibus_id, numero, fila, coluna, lado)
    """
    vals = []
    for n in range(1, capacidade + 1):
        aid = id_inicial + n - 1
        fila = (n - 1) // 4 + 1
        coluna = (n - 1) % 4 + 1
        lado = "esq" if coluna <= 2 else "dir"
        vals.append(f"({aid}, {onibus_id}, {n}, {fila}, {coluna}, '{lado}')")
    return vals, id_inicial + capacidade


def gerar_sql(xlsx_path: Path, saida_path: Path):
    print(f"Lendo planilha: {xlsx_path}")
    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)

    # ------------------------------------------------------------------ #
    # 1. Coleta de dados brutos por rota                                  #
    # ------------------------------------------------------------------ #
    rotas_raw = {}
    for num, aba_adm, aba_turno, cidade in PARES_ROTA:
        adm_dados  = ler_aba_adm(wb[aba_adm])   if aba_adm   in wb.sheetnames else []
        tur_dados  = ler_aba_turno(wb[aba_turno]) if aba_turno in wb.sheetnames else []
        nome_r_adm = extrair_nome_rota(wb[aba_adm])   if aba_adm   in wb.sheetnames else aba_adm
        nome_r_tur = extrair_nome_rota(wb[aba_turno]) if aba_turno in wb.sheetnames else aba_turno
        rotas_raw[num] = {
            "nome_adm":  nome_r_adm,
            "nome_tur":  nome_r_tur,
            "cidade":    cidade,
            "adm":       adm_dados,
            "turno":     tur_dados,
        }
        print(f"  Rota {num}: {len(adm_dados)} ADM, {len(tur_dados)} Turno")

    wb.close()

    # ------------------------------------------------------------------ #
    # 2. Deduplicação de colaboradores                                    #
    # ------------------------------------------------------------------ #
    colaboradores: dict[str, dict] = {}  # nome_norm → {id, nome, ...}
    colab_seq = [1]

    def get_colab(dados: dict, rota_id: int) -> dict:
        key = normalizar_nome(dados["nome"])
        if key not in colaboradores:
            c = {
                "id":        colab_seq[0],
                "nome":      dados["nome"].title(),
                "matricula": f"IMP{colab_seq[0]:05d}",
                "cargo":     dados.get("cargo"),
                "bairro":    dados.get("bairro"),
                "telefone":  dados.get("telefone"),
                "empresa":   dados.get("empresa", "ALISEO"),
                "regime":    dados.get("regime", "turno"),
                "rota_id":   rota_id,
            }
            colaboradores[key] = c
            colab_seq[0] += 1
        return colaboradores[key]

    # Passa 1: registra todos os colaboradores
    for num, rd in rotas_raw.items():
        for d in rd["adm"]:
            get_colab(d, num)
        for d in rd["turno"]:
            get_colab(d, num)

    # ------------------------------------------------------------------ #
    # 3. Constrói estrutura de IDs (Rota, Onibus, Assento)               #
    # ------------------------------------------------------------------ #
    rota_id_map  = {}  # num → rota_id
    adm_oid_map  = {}  # num → onibus_id
    tur_oid_map  = {}  # num → onibus_id
    # assento: (onibus_id, num_assento) → assento_db_id
    assento_map  = {}

    rota_inserts   = []
    onibus_inserts = []
    assento_vals   = []

    oid_seq = [1]
    ass_id  = [1]

    for num, rd in sorted(rotas_raw.items()):
        rid = num  # rota_id = número da rota (1-4)
        rota_id_map[num] = rid
        nome_rota = f"{rd['nome_adm']} / {rd['nome_tur']}"
        rota_inserts.append(
            f"({rid}, {sql_str(nome_rota)}, {sql_str(rd['cidade'])}, NULL, NULL)"
        )

        # Ônibus ADM
        adm_oid = oid_seq[0]; oid_seq[0] += 1
        adm_oid_map[num] = adm_oid
        onibus_inserts.append(
            f"({adm_oid}, {sql_str(f'ADM-0{num}')}, 'admin', {ADM_CAP}, {rid}, 1, 0)"
        )
        vals, ass_id[0] = gerar_assentos_vals(adm_oid, ADM_CAP, ass_id[0])
        assento_vals += vals
        for n in range(1, ADM_CAP + 1):
            assento_map[(adm_oid, n)] = ass_id[0] - ADM_CAP + n - 1

        # Ônibus Turno
        tur_oid = oid_seq[0]; oid_seq[0] += 1
        tur_oid_map[num] = tur_oid
        onibus_inserts.append(
            f"({tur_oid}, {sql_str(f'TUR-0{num}')}, 'micro', {TUR_CAP}, {rid}, 1, 0)"
        )
        vals, ass_id[0] = gerar_assentos_vals(tur_oid, TUR_CAP, ass_id[0])
        assento_vals += vals
        for n in range(1, TUR_CAP + 1):
            assento_map[(tur_oid, n)] = ass_id[0] - TUR_CAP + n - 1

    # Corrige mapa de assentos (há um off-by-one nas iterações acima)
    # Recalcula de forma limpa:
    assento_map.clear()
    ass_ptr = 1
    for num in sorted(rotas_raw):
        adm_oid = adm_oid_map[num]
        for n in range(1, ADM_CAP + 1):
            assento_map[(adm_oid, n)] = ass_ptr
            ass_ptr += 1
        tur_oid = tur_oid_map[num]
        for n in range(1, TUR_CAP + 1):
            assento_map[(tur_oid, n)] = ass_ptr
            ass_ptr += 1

    # ------------------------------------------------------------------ #
    # 4. Monta INSERT de alocações                                        #
    # ------------------------------------------------------------------ #
    aloc_vals = []
    aloc_seq = [1]
    ocupados_adm = {}  # (onibus_id, assento_num, letra) → nome
    ocupados_tur = {}

    avisos = []

    for num, rd in sorted(rotas_raw.items()):
        adm_oid = adm_oid_map[num]
        tur_oid = tur_oid_map[num]

        # ADM
        for d in rd["adm"]:
            key = normalizar_nome(d["nome"])
            c = colaboradores.get(key)
            if not c:
                continue
            if d["assento"] is None:
                continue
            nass = d["assento"]
            if nass < 1 or nass > ADM_CAP:
                avisos.append(f"ADM-0{num}: assento {nass} fora do range (1-{ADM_CAP}) — {d['nome']}")
                continue
            chave = (adm_oid, nass, "ADM")
            if chave in ocupados_adm:
                avisos.append(f"ADM-0{num}: assento {nass} duplicado — {d['nome']} (já: {ocupados_adm[chave]})")
                continue
            ocupados_adm[chave] = d["nome"]
            aid = assento_map[(adm_oid, nass)]
            aloc_vals.append(f"({aloc_seq[0]}, {aid}, {c['id']}, 'ADM')")
            aloc_seq[0] += 1

        # Turno
        for d in rd["turno"]:
            key = normalizar_nome(d["nome"])
            c = colaboradores.get(key)
            if not c:
                continue
            if d["assento"] is None or not d["letras"]:
                continue
            nass = d["assento"]
            if nass < 1 or nass > TUR_CAP:
                avisos.append(f"TUR-0{num}: assento {nass} fora do range (1-{TUR_CAP}) — {d['nome']}")
                continue
            aid = assento_map[(tur_oid, nass)]
            for letra in d["letras"]:
                chave = (tur_oid, nass, letra)
                if chave in ocupados_tur:
                    avisos.append(f"TUR-0{num}: assento {nass} letra {letra} duplicado — {d['nome']} (já: {ocupados_tur[chave]})")
                    continue
                ocupados_tur[chave] = d["nome"]
                aloc_vals.append(f"({aloc_seq[0]}, {aid}, {c['id']}, {sql_str(letra)})")
                aloc_seq[0] += 1

    # ------------------------------------------------------------------ #
    # 5. Monta INSERT de colaboradores (rota_id = rota onde aparece pela vez)
    # ------------------------------------------------------------------ #
    colab_vals = []
    for c in sorted(colaboradores.values(), key=lambda x: x["id"]):
        colab_vals.append(
            f"({c['id']}, {sql_str(c['nome'])}, {sql_str(c['matricula'])}, "
            f"{sql_str(c.get('cargo'))}, {sql_str(c.get('telefone'))}, "
            f"'{c['regime']}', {sql_str('Campos dos Goytacazes')}, "
            f"{sql_str(c.get('bairro'))}, {sql_str(c['empresa'])}, "
            f"{c['rota_id']})"
        )

    # ------------------------------------------------------------------ #
    # 6. Monta arquivo SQL final                                          #
    # ------------------------------------------------------------------ #
    def bloco(header, vals, colunas):
        if not vals:
            return []
        linhas = [f"INSERT INTO {header} ({colunas}) VALUES"]
        linhas.append(",\n".join(f"  {v}" for v in vals) + ";")
        return linhas

    sql_lines = [
        "-- ===========================================================",
        "-- Importacao gerada por scripts/importar_planilha.py",
        "-- Para aplicar:",
        "--   docker exec -i busio_db sh -c \\",
        "--     'mysql -u\"$MYSQL_USER\" -p\"$MYSQL_PASSWORD\" \"$MYSQL_DATABASE\"' < dados_reais.sql",
        "-- ===========================================================",
        "",
        "SET NAMES utf8mb4;",
        "SET FOREIGN_KEY_CHECKS=0;",
        "TRUNCATE TABLE solicitacoes_hora_extra;",
        "TRUNCATE TABLE excecoes_data;",
        "TRUNCATE TABLE alocacoes_fixas;",
        "TRUNCATE TABLE assentos;",
        "TRUNCATE TABLE colaboradores;",
        "TRUNCATE TABLE onibus;",
        "TRUNCATE TABLE rotas;",
        "DELETE FROM configuracoes WHERE chave = 'turno_letra_ativa';",
        "INSERT INTO configuracoes (chave, valor) VALUES ('turno_letra_ativa', 'A');",
        "SET FOREIGN_KEY_CHECKS=1;",
        "",
    ]

    sql_lines += bloco(
        "rotas", rota_inserts,
        "id, nome, cidade, bairros, horarios"
    ) + [""]

    sql_lines += bloco(
        "onibus", onibus_inserts,
        "id, identificador, tipo, capacidade, rota_id, ativo, exemplo"
    ) + [""]

    sql_lines += bloco(
        "assentos", assento_vals,
        "id, onibus_id, numero, fila, coluna, lado"
    ) + [""]

    sql_lines += bloco(
        "colaboradores", colab_vals,
        "id, nome, matricula, setor, telefone, regime, cidade, bairro, empresa, rota_id"
    ) + [""]

    sql_lines += bloco(
        "alocacoes_fixas", aloc_vals,
        "id, assento_id, colaborador_id, turno_letra"
    ) + [""]

    saida_path.write_text("\n".join(sql_lines), encoding="utf-8")

    # ------------------------------------------------------------------ #
    # 7. Resumo                                                           #
    # ------------------------------------------------------------------ #
    print()
    print("=" * 60)
    print(f"SQL gerado em: {saida_path}")
    print(f"  Rotas:        {len(rota_inserts)}")
    print(f"  Ônibus:       {len(onibus_inserts)}")
    print(f"  Assentos:     {len(assento_vals)}")
    print(f"  Colaboradores:{len(colab_vals)}")
    print(f"  Alocações:    {len(aloc_vals)}")
    if avisos:
        print(f"\n  AVISOS ({len(avisos)}):")
        for a in avisos:
            print(f"    ! {a}")
    print("=" * 60)
    print()
    print("Para aplicar ao banco (Docker deve estar rodando):")
    print('  docker exec -i busio_db sh -c \'mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE"\' < dados_reais.sql')
    print()
    print("Lembre de desativar o seed para não sobrescrever na próxima subida:")
    print("  .env -> SEED_ON_START=false")


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    xlsx_path = Path(sys.argv[1])
    saida = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("dados_reais.sql")

    if not xlsx_path.exists():
        sys.exit(f"Arquivo não encontrado: {xlsx_path}")

    gerar_sql(xlsx_path, saida)
