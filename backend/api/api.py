import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

import settings
import api.healthchecker as hc
from infrastructure.postgres import database
from .routers import auth_router


@asynccontextmanager
async def init_tables(app: FastAPI):
    urls_to_check = [f"{settings.minio_settings.URI}/minio/health/live"]

    hc.Readiness(urls=urls_to_check, logger=app.state.Logger).run()

    # Init DB tables if not exist
    # async with database.engine.begin() as conn:
    #     await conn.run_sync(database.Base.metadata.create_all)
    #     await init_db(conn, database.fd)

    yield


origins = ["*"]
middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )
]
app = FastAPI(
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    middleware=middleware,
    lifespan=init_tables,
)

app.state.Logger = logging.getLogger(name="deepscriptum_backend")
app.state.Logger.setLevel("DEBUG")

app.include_router(auth_router, prefix="/api")


@app.get("/")
async def root():
    return {"info": "DeepScriptum API. See /docs for documentation"}


@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    request.state.db = database.async_session_factory()
    try:
        response = await call_next(request)
    except Exception as exc:
        detail = getattr(exc, "detail", None)
        unexpected_error = not detail
        if unexpected_error:
            args = getattr(exc, "args", None)
            detail = args[0] if args else str(exc)
        status_code = getattr(exc, "status_code", 500)
        response = JSONResponse(
            content={"detail": str(detail), "success": False}, status_code=status_code
        )
    finally:
        await request.state.db.close()
    return response
