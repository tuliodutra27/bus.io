from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.db import Base, SessionLocal, engine, wait_for_db
from app.dependencies import NaoAutenticado
from app.routers import dashboard, hora_extra, onibus
from app.routers import auth
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
