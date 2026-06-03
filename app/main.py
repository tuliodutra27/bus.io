from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.db import Base, SessionLocal, engine, wait_for_db
from app.dependencies import NaoAutenticado, SemPermissao
from app.routers import auth, dashboard, hora_extra, onibus
from app.services.seed import seed

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(SessionMiddleware, secret_key=settings.SESSION_SECRET)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(onibus.router)
app.include_router(hora_extra.router)


@app.exception_handler(NaoAutenticado)
async def handle_nao_autenticado(request: Request, exc: NaoAutenticado):
    return RedirectResponse("/login", status_code=302)


@app.exception_handler(SemPermissao)
async def handle_sem_permissao(request: Request, exc: SemPermissao):
    # Requisições HTMX recebem conteúdo inline para trocar no alvo (HTMX descarta 4xx por padrão)
    if request.headers.get("HX-Request"):
        return HTMLResponse(
            content='<div class="bg-red-50 border border-red-200 text-red-700 rounded-lg p-4 text-sm max-w-2xl">'
                    'Sem permissão para realizar esta ação.'
                    '</div>',
            status_code=200,
        )
    return HTMLResponse(
        content="""
        <!DOCTYPE html><html lang="pt-br"><head><meta charset="utf-8">
        <script src="https://cdn.tailwindcss.com"></script></head>
        <body class="bg-slate-100 min-h-screen flex items-center justify-center">
          <div class="text-center">
            <p class="text-6xl font-bold text-slate-300">403</p>
            <p class="mt-2 text-lg text-slate-600">Sem permissão para esta ação.</p>
            <a href="/" class="mt-4 inline-block text-sky-600 hover:underline text-sm">Voltar ao painel</a>
          </div>
        </body></html>
        """,
        status_code=403,
    )


@app.on_event("startup")
def on_startup() -> None:
    wait_for_db()
    Base.metadata.create_all(bind=engine)
    if settings.SEED_ON_START:
        db = SessionLocal()
        try:
            seed(db)
        finally:
            db.close()


@app.get("/health")
def health():
    return {"status": "ok"}
