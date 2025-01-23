from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from jinja2 import J

app = FastAPI(
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)
templates = Jinja2Templates("templates")


@app.get("/auth/login")
async def login():
    return templates.TemplateResponse(name="login.html")


# @app.get("/auth/logout")
# async def login():
#     return templates.TemplateResponse(name="login.html")


@app.get("/auth/register")
async def login():
    return templates.TemplateResponse(name="register.html")
