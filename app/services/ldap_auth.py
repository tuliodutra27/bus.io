"""Autenticação via Active Directory (LDAP).

Fluxo:
1. Bind como username@domínio com a senha fornecida.
2. Busca o objeto do usuário no AD (sAMAccountName).
3. Verifica se o CN do grupo de acesso está em algum dos valores de memberOf.
4. Retorna UsuarioAD com nome de exibição, ou None em caso de falha/sem permissão.
"""

from dataclasses import dataclass

from ldap3 import ALL, Connection, Server
from ldap3.core.exceptions import LDAPException

from app.config import settings


@dataclass
class UsuarioAD:
    username: str
    nome: str


def autenticar(username: str, password: str) -> UsuarioAD | None:
    """Autentica no AD e verifica pertencimento ao grupo de acesso.

    Retorna UsuarioAD em sucesso; None se credenciais inválidas, usuário não
    encontrado ou fora do grupo GRP_App_Acessar_Bus.io.
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
        group_upper = settings.LDAP_GROUP.upper()

        if not any(group_upper in dn for dn in member_of):
            conn.unbind()
            return None

        nome = str(entry.displayName) if entry.displayName else username
        conn.unbind()
        return UsuarioAD(username=username, nome=nome)

    except LDAPException:
        return None
