# bus.io

Gestão de assentos dos ônibus fretados que levam colaboradores até o **Porto do Açu**,
saindo de **Campos dos Goytacazes** e **São João da Barra**.

Resolve a dor de hoje: saber em tempo real **quem senta onde**, **quantas vagas restam** em cada
ônibus e marcar de forma simples o assento de quem precisa de **hora extra** (colaborador
administrativo que volta no ônibus de turno).

> **Status: MVP.** Dois ônibus são 100% funcionais (1 administrativo `ADM-01` + 1 de turno
> `TUR-01`, na mesma rota, para viabilizar o fluxo de hora extra). Os demais (3 admin + 3 turno)
> aparecem apenas para **exibição de exemplo**. Frota real: 4 admin + 4 turno.

## Funcionalidades

- **Login via Active Directory** — acesso restrito ao grupo `GRP_App_Acessar_Bus.io`.
- **Painel** com todos os ônibus, ocupação do dia e vagas livres.
- **Mapa de assentos** interativo (admin = 50 lugares, micro de turno = 30) — clique no assento
  para ver os dados do colaborador.
- **Modelo de ocupação híbrido**: roster fixo (assento permanente) + exceções por data
  (hora extra, ausência, eventual).
- **Fluxo de hora extra**: escolha o colaborador → o sistema sugere o ônibus de turno da rota dele
  → marque um assento livre para a data.

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
```

Edite o `.env` com os valores reais do seu ambiente:

```env
# Banco de dados (pode manter os defaults)
MYSQL_ROOT_PASSWORD=rootpass
MYSQL_DATABASE=busio
MYSQL_USER=busio
MYSQL_PASSWORD=busio
SEED_ON_START=true

# Active Directory — ajuste para o seu ambiente
LDAP_SERVER=ldap://dc.aliseo.local       # endereço do Domain Controller
LDAP_DOMAIN=aliseo.local                  # domínio (para login UPN: user@aliseo.local)
LDAP_BASE_DN=DC=aliseo,DC=local           # base DN de busca
LDAP_GROUP=GRP_App_Acessar_Bus.io         # grupo AD com permissão de acesso

# Sessão — gere um valor aleatório para produção:
# python3 -c "import secrets; print(secrets.token_hex(32))"
SESSION_SECRET=troque-por-valor-aleatorio-longo
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

### 3. Suba os containers

```bash
docker compose up --build
```

Na primeira subida o banco é criado e populado com dados de exemplo.

- App: **http://localhost:8000**
- Health check: http://localhost:8000/health
- MySQL (acesso externo): `localhost:3307` (user `busio` / senha `busio`)

> **Nota:** a porta 3307 é usada no host para evitar conflito com um MySQL já instalado no
> servidor. Dentro dos containers a comunicação continua em 3306.

### Parar e zerar o banco

```bash
docker compose down -v   # remove containers e volume do banco
docker compose up --build
```

## Autenticação

O acesso é restrito à **equipe de logística** via Active Directory.

Para liberar acesso a um usuário, adicione-o ao grupo **`GRP_App_Acessar_Bus.io`** no AD.

O app usa o login `usuario@domínio` (UPN) para autenticar no AD e verifica o atributo
`memberOf` do usuário. Se o grupo de acesso não aparecer, o login é recusado mesmo com
credenciais corretas.

## Estrutura

```
bus.io/
├── app/
│   ├── main.py                 # app FastAPI + startup (cria tabelas e seed)
│   ├── config.py               # settings via env (banco, LDAP, sessão)
│   ├── db.py                   # engine/sessão MySQL + espera o banco subir
│   ├── dependencies.py         # require_login (dependency FastAPI)
│   ├── models.py               # Rota, Onibus, Assento, Colaborador, AlocacaoFixa,
│   │                           # ExcecaoData, SolicitacaoHoraExtra
│   ├── services/
│   │   ├── ldap_auth.py        # autenticação e verificação de grupo no AD
│   │   ├── ocupacao.py         # cálculo: fixo − ausência + extra
│   │   └── seed.py             # dados de exemplo (2 ônibus funcionais)
│   ├── routers/
│   │   ├── auth.py             # GET/POST /login, GET /logout
│   │   ├── dashboard.py        # painel principal
│   │   ├── onibus.py           # mapa de assentos
│   │   └── hora_extra.py       # fluxo de hora extra
│   ├── templates/
│   │   ├── login.html          # tela de login
│   │   ├── base.html           # layout + modal global
│   │   └── partials/           # seat_map, seat_detail, hora_extra_resultado
│   └── static/css/app.css      # estilo do mapa de assentos
├── .env.example                # modelo de configuração
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## Modelo de dados

```
Rota ──< Onibus ──< Assento ──1 AlocacaoFixa >── Colaborador
                        └──< ExcecaoData(hora_extra|ausencia|eventual) >── Colaborador
Rota ──< Colaborador
SolicitacaoHoraExtra (histórico) ── Colaborador / Onibus / Assento
```

Ocupação de um ônibus numa data:

```
ocupação = AlocacaoFixa − ausências(data) + extras(data)
```

## Roadmap

- [x] Painel + mapa de assentos interativo
- [x] Modelo híbrido (roster fixo + exceções por data)
- [x] Fluxo de hora extra com sugestão de ônibus pela rota
- [x] Login via Active Directory (grupo GRP_App_Acessar_Bus.io)
- [ ] CRUD de colaboradores / ônibus / rotas pela interface
- [ ] Migrations com Alembic
- [ ] Ativar todos os 8 ônibus reais (4 admin + 4 turno)
- [ ] Relatórios e exportação de ocupação

---

Projeto interno de logística — Porto do Açu.
