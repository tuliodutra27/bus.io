import os


def _required(key: str) -> str:
    """Lê variável de ambiente obrigatória; levanta erro claro se ausente."""
    val = os.getenv(key)
    if not val:
        raise RuntimeError(
            f"Variável de ambiente obrigatória não definida: {key}\n"
            f"Crie o arquivo .env na raiz do projeto (veja .env.example)."
        )
    return val


class Settings:
    """Configuração lida exclusivamente de variáveis de ambiente.

    Todas as credenciais vêm do .env — nenhum valor sensível é hardcoded aqui.
    """

    # Banco de dados — construído a partir das vars individuais ou de DATABASE_URL
    @property
    def DATABASE_URL(self) -> str:
        url = os.getenv("DATABASE_URL")
        if url:
            return url
        host = os.getenv("MYSQL_HOST", "db")
        port = os.getenv("MYSQL_PORT", "3306")
        user = _required("MYSQL_USER")
        pwd  = _required("MYSQL_PASSWORD")
        db   = _required("MYSQL_DATABASE")
        return f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{db}"

    SEED_ON_START: bool = os.getenv("SEED_ON_START", "true").lower() == "true"
    APP_NAME: str = "bus.io"

    CIDADES = ["Campos dos Goytacazes", "São João da Barra"]

    # Active Directory (LDAP)
    LDAP_SERVER: str = os.getenv("LDAP_SERVER", "ldap://dc.aliseo.local")
    LDAP_DOMAIN: str = os.getenv("LDAP_DOMAIN", "aliseo.local")
    LDAP_BASE_DN: str = os.getenv("LDAP_BASE_DN", "DC=aliseo,DC=local")

    LDAP_GROUP_ADMIN:     str = os.getenv("LDAP_GROUP_ADMIN",     "GRP_App_Bus.io_Admin")
    LDAP_GROUP_LOGISTICA: str = os.getenv("LDAP_GROUP_LOGISTICA", "GRP_App_Bus.io_Logistica")
    LDAP_GROUP_VIEWER:    str = os.getenv("LDAP_GROUP_VIEWER",    "GRP_App_Bus.io_Viewer")

    # Sessão HTTP — obrigatório em produção
    SESSION_SECRET: str = _required("SESSION_SECRET")


settings = Settings()
