from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.services.ldap_auth import autenticar
from app.templating import templates

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, erro: str | None = None):
    if request.session.get("username"):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "erro": erro})


@router.post("/login")
def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    usuario = autenticar(username.strip(), password)
    if usuario is None:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "erro": "Usuário ou senha inválidos, ou sem permissão de acesso.",
                "username": username,
            },
            status_code=401,
        )
    request.session["username"] = usuario.username
    request.session["nome"] = usuario.nome
    request.session["role"] = usuario.role
    return RedirectResponse("/", status_code=302)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=302)
