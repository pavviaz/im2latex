from uuid import uuid4

from fastapi import APIRouter, Depends, Response, UploadFile, File, Request
from fastapi.responses import JSONResponse
from celery import Celery
from celery.result import AsyncResult
import sqlalchemy as sa

from domain.auth.model import BaseUser, RoleEnum
from domain.exceptions import BaseAPIException
from infrastructure.postgres.models.document import DocumentDAO
from infrastructure.postgres.models.user import DocumentUserDAO
from api.dependencies import get_current_user
import settings
from api.utils import process_file


router = APIRouter(prefix="/documents", tags=["Documents"])

celery = Celery(__name__)
celery.conf.broker_url = settings.rabbitmq_settings.URI


@router.get("/")
async def get_all_docs(
    request: Request,
    user: str = Depends(get_current_user),
):
    _, pg_session = request.state.s3, request.state.db
    user_docs = {}

    q = (
        sa.select(DocumentUserDAO)
        .where(DocumentUserDAO.user_id == user)
        .order_by(DocumentUserDAO.last_access_at.asc())
    )
    q = await pg_session.execute(q)
    rows = q.scalars().all()

    if not rows:
        return user_docs

    for row in rows:
        q = sa.select(DocumentDAO).where(DocumentDAO.id == row.document_id)
        q = await pg_session.execute(q)
        res = q.fetchone()

        user_docs.update(
            {
                str(row.document_id): {
                    "name": res[0].name,
                    "s3_md_id": str(res[0].s3_md_id),
                }
            }
        )

    return JSONResponse(content=user_docs)


@router.post("/ocr")
async def create_ocr_task(
    request: Request,
    document: UploadFile = File(),
    user: str = Depends(get_current_user),
):
    s3_session, pg_session = request.state.s3, request.state.db

    doc_binary = document.file.read()
    document.file.seek(0)

    _ = process_file(doc_binary)  # check if file is pdf
    doc_s3_uuid = str(uuid4())

    try:
        await s3_session.upload_fileobj(
            document.file,
            settings.minio_settings.BUCKET,
            doc_s3_uuid,
            ExtraArgs={
                "Metadata": {
                    "ext": document.filename.split(".")[-1],
                },
            },
        )
    except:
        raise BaseAPIException(status_code=500, detail="S3 error")

    pg_raw_document = DocumentDAO(
        id=doc_s3_uuid,
        name=".".join(document.filename.split(".")[:-1]),
        s3_raw_id=doc_s3_uuid,
    )
    pg_session.add(pg_raw_document)
    await pg_session.commit()

    pg_doc_user = DocumentUserDAO(
        user_id=user, document_id=doc_s3_uuid, role=RoleEnum.owner
    )
    pg_session.add(pg_doc_user)
    await pg_session.commit()

    celery.send_task("images", task_id=doc_s3_uuid)

    return JSONResponse(
        status_code=201,
        content={
            "msg": "The task has been created successfully",
            "doc_id": doc_s3_uuid,
        },
    )


@router.get("/{document_id}/status")
async def check_doc_status(
    request: Request,
    document_id: str,
    user: BaseUser = Depends(get_current_user),
):
    _, pg_session = request.state.s3, request.state.db

    q = sa.select(DocumentDAO).where(DocumentDAO.id == document_id)
    q = await pg_session.execute(q)
    res = q.fetchone()[0]

    if res.s3_md_id:
        return {"s3_md_id": res.s3_md_id}

    return {"s3_md_id": "0"}


@router.get("/{document_id}")
async def get_document(
    request: Request,
    document_id: str,
    user: BaseUser = Depends(get_current_user),
):
    s3_session, _ = request.state.s3, request.state.db

    response = await s3_session.get_object(
        Bucket=settings.minio_settings.BUCKET, Key=document_id
    )
    async with response["Body"] as stream:
        content = await stream.read()

    return {"content": content.decode("utf-8")}
