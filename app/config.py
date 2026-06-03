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

    # Autenticação via Active Directory (LDAP)
    LDAP_SERVER: str = os.getenv("LDAP_SERVER", "ldap://dc.aliseo.local")
    LDAP_DOMAIN: str = os.getenv("LDAP_DOMAIN", "aliseo.local")
    LDAP_BASE_DN: str = os.getenv("LDAP_BASE_DN", "DC=aliseo,DC=local")

    # Grupos de acesso — apenas o CN do grupo (verificação por substring no memberOf)
    # Nível 1: administrador — acesso total (futuro CRUD)
    LDAP_GROUP_ADMIN: str = os.getenv("LDAP_GROUP_ADMIN", "GRP_App_Bus.io_Admin")
    # Nível 2: logística — pode marcar/alterar dados
    LDAP_GROUP_LOGISTICA: str = os.getenv("LDAP_GROUP_LOGISTICA", "GRP_App_Bus.io_Logistica")
    # Nível 3: visualização — somente leitura
    LDAP_GROUP_VIEWER: str = os.getenv("LDAP_GROUP_VIEWER", "GRP_App_Bus.io_Viewer")

    # Chave de assinatura da sessão HTTP (cookie seguro)
    SESSION_SECRET: str = os.getenv("SESSION_SECRET", "dev-secret-troque-em-producao")


settings = Settings()
