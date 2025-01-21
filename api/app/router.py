import os
import uuid
from io import BytesIO
import base64

from fastapi import APIRouter, UploadFile, File, Cookie, Form
from fastapi.responses import JSONResponse
from fastapi import status
from celery import Celery
from celery.result import AsyncResult
from pdf2image import convert_from_bytes

from utils import process_file


celery = Celery(__name__)
celery.conf.broker_url = os.getenv("CELERY_BROKER_URL")
celery.conf.result_backend = os.getenv("CELERY_RESULT_BACKEND")

router = APIRouter(tags=["tasker"])


@router.get("/")
def hello_world():
    """
    Hello world endpoint
    """
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"msg": "Hello, world!"},
    )


@router.post("/transform")
async def create_transform_task(
    decode_type: str = Form(default="md"),
    file: UploadFile = File(),
    proc_task_id: str | None = Cookie(default="-1"),
):
    """
    Create a pdf processing task.

    This endpoint is used to create a pdf processing OCR task.
    It checks if there is an ongoing task with
    the same task ID and returns a conflict response if so.
    If there is no ongoing task, it generates a new task ID, sends
    a task to a Celery worker, and returns a success response with the task ID.

    Args:
        decode_type (str): The desired output format,
        can be 'md'.
        file (UploadFile): User's document to be processed.
        proc_task_id (str, optional): The task ID of the OCR task.
        Passed as a cookie in the request. Defaults to "-1".

    Returns:
        JSONResponse: Success response with status code 201 and the new task ID.
        Conflict response with status code 409
        if there is an ongoing task with the same task ID.
    """
    res = AsyncResult(id=proc_task_id)
    if res.status in ["STARTED", "RETRY"]:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"msg": "Please wait until current task completes"},
        )
    else:
        res.forget()

    file_binary = await file.read()

    file_type, data = await process_file(file_binary)
    
    # pdf_base64 = []
    # for img in pdf_imgs:
    #     buffered = BytesIO()
    #     img.save(buffered, format="JPEG")
    #     pdf_base64.append(base64.b64encode(buffered.getvalue()).decode())

    task_id = str(uuid.uuid4())
    celery.send_task("images", args=(pdf_base64, decode_type), task_id=task_id)

    resp = JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"msg": "The task has been created successfully", "task_id": task_id},
    )
    resp.set_cookie(key="proc_task_id", value=task_id)
    return resp


@router.get("/status")
async def check_proc_status(proc_task_id: str | None = Cookie(default="-1")):
    """
    Check the status of a processing task.

    Args:
        proc_task_id (str, optional): The task ID of the OCR task.
        Passed as a cookie in the request. Defaults to "-1".

    Returns:
        JSONResponse with corresponding message and content
        if available
    """
    res = AsyncResult(id=proc_task_id)

    if res.status == "SUCCESS":
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"msg": "Processed successfully", "content": res.result},
        )
    elif res.status == "PENDING":
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={"msg": "Please, start the task"},
        )
    elif res.status in ["STARTED", "RETRY"]:
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={"msg": "Please wait, your document is being processed..."},
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"msg": "Oops... Something went wrong with your document"},
        )
