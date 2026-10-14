from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .database import Base, engine

from .routes.pages import router as pages_router
from .routes.auth import router as auth_router


# Create database tables

Base.metadata.create_all(
    bind=engine
)


app = FastAPI(
    title="IEEE RAS NIT Silchar",
    description="IEEE Robotics & Automation Society — NIT Silchar",
    version="1.0.0"
)


# Static files

app.mount(
    "/static",
    StaticFiles(
        directory="app/static"
    ),
    name="static"
)


# Routes

app.include_router(
    pages_router
)

app.include_router(
    auth_router
)


@app.get("/health")
def health():

    return {
        "status": "ok"
    }