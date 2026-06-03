# bus.io

Gestão de assentos dos ônibus fretados que levam colaboradores até o **Porto do Açu**,
saindo de **Campos dos Goytacazes** e **São João da Barra**.

Resolve a dor central: saber em tempo real **quem senta onde**, **quantas vagas restam** em cada
ônibus e marcar o assento de quem precisa de **hora extra** (colaborador administrativo que volta
no ônibus de turno).

## Funcionalidades

- **Login via Active Directory** — 3 níveis de acesso configurados por grupos AD no `.env`.
- **Painel** com todos os ônibus, ocupação do dia e vagas livres — clique em qualquer card para ver o mapa de assentos em modal.
- **Mapa de assentos** interativo — admin 50 lugares, turno 30 — modal com dados do colaborador.
- **Modelo de ocupação híbrido**: roster fixo + exceções por data (hora extra, ausência, eventual).
- **Fluxo de hora extra** com confirmação: escolha o colaborador → sistema sugere o ônibus de turno da rota → marque um assento livre (caixa de confirmação antes de salvar).
- **Ciclo de turnos A/B/C/D**: cada ônibus de turno tem um mapa de assentos por letra; a letra ativa global é controlada pelo sistema.
- **Colaborador em múltiplos ônibus**: sem restrição de um colaborador por ônibus (comum em treinamentos e transições).

## Frota

| Tipo | Quantidade | Assentos | Horário |
|---|---|---|---|
| Administrativo | 4 | 50 | Seg–Qui 07h–17h / Sex 07h–16h |
| Turno (micro) | 4 | 30 | Todos os dias (07h–19h ou 19h–07h) |

## Stack

| Camada | Tecnologia |
|---|---|
| Backend / API | FastAPI + Uvicorn |
| Banco | MySQL 8 |
| ORM | SQLAlchemy 2 + PyMySQL |
| Frontend | Jinja2 + HTMX + Alpine.js + Tailwind (CDN, sem build) |
| Autenticação | LDAP3 (Active Directory) + SessionMiddleware |
| Infra | Docker Compose (app + db) |

## Como rodar

Pré-requisito: **Docker** e **Docker Compose**. Nada mais precisa ser instalado localmente.

### 1. Clone o repositório

```bash
git clone https://github.com/tuliodutra27/bus.io.git
cd bus.io
```

### 2. Crie o arquivo `.env`

O `.env` fica na **raiz do projeto**, na mesma pasta do `docker-compose.yml`.

```bash
cp .env.example .env
nano .env   # edite com os valores reais
```

Estrutura do `.env`:

```env
# Banco de dados — todos os valores são obrigatórios
MYSQL_ROOT_PASSWORD=senha_root_aqui
MYSQL_DATABASE=busio
MYSQL_USER=busio
MYSQL_PASSWORD=senha_busio_aqui

# Popula o banco com dados de exemplo na primeira subida
SEED_ON_START=true

# Active Directory — ajuste para o seu ambiente
LDAP_SERVER=ldap://dc.aliseo.local
LDAP_DOMAIN=aliseo.local
LDAP_BASE_DN=DC=aliseo,DC=local

# Grupos de acesso (CN do grupo no AD)
LDAP_GROUP_ADMIN=GRP_App_Bus.io_Admin         # leitura + escrita + configuração
LDAP_GROUP_LOGISTICA=GRP_App_Bus.io_Logistica # leitura + marcar hora extra
LDAP_GROUP_VIEWER=GRP_App_Bus.io_Viewer       # somente leitura

# Sessão — gere com:
# python3 -c "import secrets; print(secrets.token_hex(32))"
SESSION_SECRET=valor_aleatorio_longo_aqui
```

> **Onde fica o `.env`?**
> ```
> bus.io/
> ├── .env                ← aqui
> ├── .env.example
> ├── docker-compose.yml
> ├── Dockerfile
> └── app/
> ```

> **Nenhuma credencial é hardcoded no código.** A aplicação recusa iniciar se `MYSQL_USER`,
> `MYSQL_PASSWORD`, `MYSQL_DATABASE` ou `SESSION_SECRET` estiverem ausentes, com mensagem clara.

### 3. Suba os containers

```bash
docker compose up --build
```

Na primeira subida o banco é criado e populado com dados de exemplo (`SEED_ON_START=true`).

- App: **http://localhost:8000**
- MySQL (acesso externo): `localhost:3307`

> **Porta 3307:** usada no host para evitar conflito com MySQL já instalado no servidor. Dentro
> dos containers a comunicação continua em 3306.

### Parar e zerar o banco

```bash
docker compose down -v   # remove containers e volume do banco
docker compose up --build
```

### Gerar SESSION_SECRET

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Execute localmente (não precisa de Docker) e cole o resultado no `.env`.

## Autenticação e níveis de acesso

O acesso é via Active Directory. Três grupos controlam o nível de permissão:

| Grupo (variável `.env`) | Permissões |
|---|---|
| `LDAP_GROUP_ADMIN` | Tudo: configurar letra ativa, gerenciar dados |
| `LDAP_GROUP_LOGISTICA` | Marcar hora extra, definir letra de turno |
| `LDAP_GROUP_VIEWER` | Somente visualização (painéis e mapas) |

O app usa login `usuario@domínio` (UPN) e verifica o atributo `memberOf`. Se o usuário
estiver em mais de um grupo, a permissão mais alta prevalece. Quem não estiver em nenhum
dos três grupos tem acesso negado.

## Ciclo de turno A/B/C/D

Os ônibus de turno operam em 4 turnos rotativos (letras A, B, C, D). Cada assento do
roster de turno é vinculado a uma letra específica.

- Na página de cada ônibus de turno, botões A/B/C/D permitem visualizar o mapa de cada ciclo.
- A **letra ativa global** (usada por padrão no dashboard e na hora extra) é armazenada no
  banco e pode ser atualizada por Admin/Logística com um clique.
- Ônibus administrativos não usam letras (são marcados como `ADM` internamente).

## Estrutura

```
bus.io/
├── app/
│   ├── main.py                 # app FastAPI + startup + exception handlers
│   ├── config.py               # settings exclusivamente via env (sem hardcode)
│   ├── db.py                   # engine/sessão MySQL + wait_for_db no boot
│   ├── dependencies.py         # require_login / require_logistica / require_admin
│   ├── models.py               # todos os modelos + LETRAS_TURNO + LETRA_ADM
│   ├── services/
│   │   ├── ldap_auth.py        # autenticação AD e verificação de grupos (3 níveis)
│   │   ├── ocupacao.py         # montar_mapa, get_letra_ativa, onibus_turno_da_rota
│   │   └── seed.py             # dados de exemplo (4 admin + 4 turno, A/B/C/D)
│   ├── routers/
│   │   ├── auth.py             # GET/POST /login, GET /logout
│   │   ├── dashboard.py        # painel principal
│   │   ├── onibus.py           # mapa de assentos + mapa-parcial + POST letra ativa
│   │   └── hora_extra.py       # fluxo de hora extra
│   ├── templates/
│   │   ├── login.html
│   │   ├── base.html           # layout + modal global + caixa de confirmação
│   │   ├── dashboard.html      # cards clicáveis → modal com mapa
│   │   ├── onibus_mapa.html    # mapa completo + seletor de letra A/B/C/D
│   │   ├── hora_extra.html
│   │   └── partials/
│   │       ├── seat_map.html           # macro do grid de assentos
│   │       ├── seat_detail.html        # conteúdo do modal de assento
│   │       ├── onibus_mapa_parcial.html # mapa resumido para o modal do dashboard
│   │       └── hora_extra_resultado.html
│   └── static/css/app.css      # estilos dos assentos
├── .env.example
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## Modelo de dados

```
Rota ──< Onibus ──< Assento ──< AlocacaoFixa(turno_letra) >── Colaborador
                        └──< ExcecaoData(hora_extra|ausencia|eventual) >── Colaborador
Rota ──< Colaborador
SolicitacaoHoraExtra (histórico) ── Colaborador / Onibus / Assento
Configuracao (chave/valor) — ex: turno_letra_ativa = "A"
```

Regra de ocupação:

```
ocupação(ônibus, data, turno_letra) = AlocacaoFixa(letra) − ausências(data) + extras(data)
```

`AlocacaoFixa` possui `turno_letra`:
- `"ADM"` para ônibus administrativos
- `"A"`, `"B"`, `"C"` ou `"D"` para ônibus de turno
- Um colaborador pode ter `AlocacaoFixa` em múltiplos ônibus/letras

## Roadmap

- [x] Painel + mapa de assentos interativo
- [x] Modelo híbrido (roster fixo + exceções por data)
- [x] Fluxo de hora extra com sugestão de ônibus pela rota
- [x] Login via Active Directory com 3 níveis de acesso (admin / logística / viewer)
- [x] Caixa de confirmação antes de marcar assento
- [x] Ciclo de turnos A/B/C/D com letra ativa global
- [x] Colaborador em múltiplos ônibus (sem restrição)
- [x] Credenciais 100% via `.env` (sem hardcode no código)
- [x] Modal de mapa no dashboard (clique no card)
- [ ] CRUD de colaboradores / ônibus / rotas pela interface
- [ ] Importação da planilha Excel com roster real
- [ ] Migrations com Alembic
- [ ] Relatórios e exportação de ocupação

---

Projeto interno de logística — Porto do Açu.
