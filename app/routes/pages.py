from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
import json
from pathlib import Path

router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


@router.get("/")
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={}
    )

@router.get("/about")
def about(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="about.html",
        context={}
    )

@router.get("/projects")
def projects(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="projects.html",
        context={}
    )


@router.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="auth/login.html",
        context={}
    )


@router.get("/register")
def register_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="auth/register.html",
        context={}
    )

MEMBERS_FILE = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "members.json"
)
@router.get("/members")
def members_page(request: Request):
    with MEMBERS_FILE.open("r", encoding="utf-8") as file:
        members = json.load(file).get("members", [])

    return templates.TemplateResponse(
        request=request,
        name="members.html",
        context={"members": members},
    )