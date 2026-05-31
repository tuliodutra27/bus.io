import os


class Settings:
    """Configuração lida de variáveis de ambiente (com defaults para dev)."""

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://busio:busio@db:3306/busio",
    )
    SEED_ON_START: bool = os.getenv("SEED_ON_START", "true").lower() == "true"
    APP_NAME: str = "bus.io"

    # Cidades atendidas (todas as rotas terminam no Porto do Açu)
    CIDADES = ["Campos dos Goytacazes", "São João da Barra"]


settings = Settings()
