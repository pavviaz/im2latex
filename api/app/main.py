import uvicorn
from fastapi import FastAPI

from app.router import router as router_dwnl
# from router import router as router_dwnl


app = FastAPI(
    title="file2md API",
    description="This service uses VLLM to transform any document \
    to MD via OCR",
    version="0.0.1",
    redoc_url=None
)

app.include_router(router_dwnl)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
