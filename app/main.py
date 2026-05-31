from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.db import Base, SessionLocal, engine, wait_for_db
from app.routers import dashboard, hora_extra, onibus
from app.services.seed import seed

app = FastAPI(title=settings.APP_NAME)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(dashboard.router)
app.include_router(onibus.router)
app.include_router(hora_extra.router)


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
