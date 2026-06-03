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
    # Apenas o CN do grupo — verificação por substring no memberOf
    LDAP_GROUP: str = os.getenv("LDAP_GROUP", "GRP_App_Acessar_Bus.io")

    # Chave de assinatura da sessão HTTP (cookie seguro)
    SESSION_SECRET: str = os.getenv("SESSION_SECRET", "dev-secret-troque-em-producao")


settings = Settings()
