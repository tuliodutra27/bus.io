# bus.io 🚌

Gestão de assentos dos ônibus fretados que levam colaboradores até o **Porto do Açu**,
saindo de **Campos dos Goytacazes** e **São João da Barra**.

Resolve a dor de hoje: saber em tempo real **quem senta onde**, **quantas vagas restam** em cada
ônibus e marcar de forma simples o assento de quem precisa de **hora extra** (colaborador
administrativo que volta no ônibus de turno).

> **Status: MVP.** Dois ônibus são 100% funcionais (1 administrativo `ADM-01` + 1 de turno
> `TUR-01`, na mesma rota, para viabilizar o fluxo de hora extra). Os demais (5 admin + 4 turno
> no total) aparecem apenas para **exibição de exemplo**.

## Funcionalidades

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
| Infra | Docker Compose (app + db) |

## Como rodar

Pré-requisito: **Docker** e **Docker Compose**. Nada mais precisa ser instalado localmente.

```bash
git clone https://github.com/tuliodutra27/bus.io.git
cd bus.io
cp .env.example .env        # opcional; os defaults já funcionam
docker compose up --build
```

Acesse: **http://localhost:8000**

Na primeira subida o banco é criado e populado com os dados de exemplo
(`SEED_ON_START=true`).

- App: http://localhost:8000
- Health check: http://localhost:8000/health
- MySQL: `localhost:3306` (user `busio` / senha `busio` / database `busio`)

## Estrutura

```
bus.io/
├── app/
│   ├── main.py                 # app FastAPI + startup (cria tabelas e seed)
│   ├── config.py               # settings via env
│   ├── db.py                   # engine/sessão MySQL + espera o banco subir
│   ├── models.py               # Rota, Onibus, Assento, Colaborador, AlocacaoFixa,
│   │                           # ExcecaoData, SolicitacaoHoraExtra
│   ├── services/
│   │   ├── ocupacao.py         # cálculo: fixo − ausência + extra
│   │   └── seed.py             # dados de exemplo (2 ônibus funcionais)
│   ├── routers/                # dashboard, onibus (mapa/assento), hora_extra
│   ├── templates/              # Jinja2 + HTMX (mapa de assentos)
│   └── static/css/app.css      # estilo do mapa
├── docker-compose.yml          # app + mysql
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

- [x] Painel + mapa de assentos interativo (2 ônibus funcionais)
- [x] Modelo híbrido (roster fixo + exceções por data)
- [x] Fluxo de hora extra com sugestão de ônibus pela rota
- [ ] CRUD de colaboradores / ônibus / rotas pela interface
- [ ] Autenticação da equipe de logística
- [ ] Migrations com Alembic
- [ ] Ativar todos os 9 ônibus (5 admin + 4 turno)
- [ ] Relatórios e exportação de ocupação

---

Projeto interno de logística — Porto do Açu.
