"""Dependências reutilizáveis do FastAPI."""

from fastapi import Request


class NaoAutenticado(Exception):
    """Levantada quando a rota exige login e não há sessão ativa."""


def require_login(request: Request) -> dict:
    """Dependency: retorna dados do usuário logado ou redireciona para /login."""
    username = request.session.get("username")
    if not username:
        raise NaoAutenticado()
    return {"username": username, "nome": request.session.get("nome", username)}
