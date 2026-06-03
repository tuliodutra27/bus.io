"""Autenticação via Active Directory (LDAP).

Fluxo:
1. Bind como username@domínio com a senha fornecida.
2. Busca o objeto do usuário no AD (sAMAccountName) e lê o atributo memberOf.
3. Determina o nível de acesso verificando os grupos em ordem de prioridade:
   admin > logistica > viewer.
4. Retorna UsuarioAD com nome e role, ou None se sem acesso.

Os nomes dos grupos são lidos de variáveis de ambiente (config.py) — nunca
hardcoded aqui.
"""

from dataclasses import dataclass

from ldap3 import ALL, Connection, Server
from ldap3.core.exceptions import LDAPException

from app.config import settings

# Ordem de prioridade: quem está em admin não precisa estar em logistica ou viewer
ROLES = [
    ("admin",     settings.LDAP_GROUP_ADMIN),
    ("logistica", settings.LDAP_GROUP_LOGISTICA),
    ("viewer",    settings.LDAP_GROUP_VIEWER),
]


@dataclass
class UsuarioAD:
    username: str
    nome: str
    role: str  # "admin" | "logistica" | "viewer"


def autenticar(username: str, password: str) -> UsuarioAD | None:
    """Autentica no AD e devolve o nível de acesso do usuário.

    Retorna UsuarioAD em sucesso; None se credenciais inválidas, usuário não
    encontrado ou sem nenhum grupo de acesso configurado.
    """
    if not username or not password:
        return None

    try:
        server = Server(settings.LDAP_SERVER, get_info=ALL, connect_timeout=5)
        user_upn = f"{username}@{settings.LDAP_DOMAIN}"

        conn = Connection(server, user=user_upn, password=password, auto_bind=True)

        conn.search(
            settings.LDAP_BASE_DN,
            f"(sAMAccountName={username})",
            attributes=["displayName", "memberOf"],
        )

        if not conn.entries:
            conn.unbind()
            return None

        entry = conn.entries[0]
        member_of = [str(dn).upper() for dn in entry.memberOf.values]

        role = None
        for role_name, group_cn in ROLES:
            if any(group_cn.upper() in dn for dn in member_of):
                role = role_name
                break

        conn.unbind()

        if role is None:
            return None

        nome = str(entry.displayName) if entry.displayName else username
        return UsuarioAD(username=username, nome=nome, role=role)

    except LDAPException:
        return None
