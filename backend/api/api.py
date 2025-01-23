from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from infrastructure.postgres.database import async_session_factory
from routers import auth_router

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
)


app.include_router(auth_router, prefix="/api")


@app.get("/")
async def root():
    return {"info": "DeepScriptum API. See /docs for documentation"}


@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    request.state.db = async_session_factory()
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


# @app.on_event("startup")
# async def startup_event():
#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.create_all)
#         await add_classifiers(conn)
