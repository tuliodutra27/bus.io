"""Dependências reutilizáveis do FastAPI."""

from fastapi import Request


class NaoAutenticado(Exception):
    """Levantada quando a rota exige login e não há sessão ativa."""


class SemPermissao(Exception):
    """Levantada quando o usuário está logado mas não tem o nível de acesso necessário."""


def require_login(request: Request) -> dict:
    """Qualquer usuário autenticado (admin, logistica ou viewer)."""
    username = request.session.get("username")
    if not username:
        raise NaoAutenticado()
    role = request.session.get("role")
    if role is None:
        # Sessão antiga sem role — força novo login para re-autenticar com nível correto
        request.session.clear()
        raise NaoAutenticado()
    return {
        "username": username,
        "nome": request.session.get("nome", username),
        "role": role,
    }


def require_logistica(request: Request) -> dict:
    """Exige nível logistica ou admin (pode marcar/alterar dados)."""
    usuario = require_login(request)
    if usuario["role"] not in ("admin", "logistica"):
        raise SemPermissao()
    return usuario


def require_admin(request: Request) -> dict:
    """Exige nível admin (acesso total)."""
    usuario = require_login(request)
    if usuario["role"] != "admin":
        raise SemPermissao()
    return usuario
