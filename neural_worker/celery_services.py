import os
import requests
from multiprocessing.pool import ThreadPool
from typing import List

from celery import Celery

import config


OPENAI_HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {os.getenv('OPENAI_KEY')}",
}
REPLACERS = {"latex": config.LATEX_REPLACER, "md": config.MD_REPLACER}


celery = Celery(__name__)
celery.conf.broker_url = os.getenv("CELERY_BROKER_URL")
celery.conf.result_backend = os.getenv("CELERY_RESULT_BACKEND")


@celery.task(
    name="images", bind=True, time_limit=600, soft_time_limit=540, track_started=True
)
def process_images(self, imgs_binary: List[str], decode_type: str):
    """
    Process images by performing OCR with VLLM.

    Args:
        imgs_binary (List[str]): A list of strings representing
        the binary data of an image.

    Returns:
        str: A string representing the processed image in base64 format.
    """
    replacer = REPLACERS[decode_type]
    imgs_enum = [(idx, img, replacer) for idx, img in enumerate(imgs_binary)]

    try:
        with ThreadPool(len(imgs_enum)) as thread_pool:
            map_results = thread_pool.starmap(_apply_map_ocr, imgs_enum)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=5)

    reduce_result = _apply_reduce_ocr(map_results, decode_type, replacer)

    return reduce_result


def _apply_map_ocr(idx: int, img_binary: str, replacer: tuple):
    payload = {
        "model": config.MODEL_NAME,
        "messages": [{"role": "user", "content": []}],
    }
    payload["messages"][0]["content"].append(
        {
            "type": "text",
            "text": config.DEFAULT_MAP_PROMPT.format(
                idx + 1, replacer[0], replacer[0], replacer[0]
            ),
        }
    )
    payload["messages"][0]["content"].append(
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{img_binary}"},
        }
    )

    response = requests.post(
        config.OPENAI_API,
        headers=OPENAI_HEADERS,
        json=payload,
    )
    content = response.json()["choices"][0]["message"]["content"]
    content = content.lstrip(replacer[1]).rstrip(replacer[2]).strip("\n")

    return content


def _apply_reduce_ocr(texts: List[str], decode_type: str, replacer: tuple):
    payload = {
        "model": config.MODEL_NAME,
        "messages": [{"role": "user", "content": []}],
    }
    payload["messages"][0]["content"].append(
        {
            "type": "text",
            "text": config.DEFAULT_REDUCE_PROMPT.format(
                len(texts),
                decode_type,
                config.REDUCE_SPLITTER,
                decode_type,
                f"\n{config.REDUCE_SPLITTER}\n".join(texts),
            ),
        }
    )

    response = requests.post(
        config.OPENAI_API,
        headers=OPENAI_HEADERS,
        json=payload,
    )
    content = response.json()["choices"][0]["message"]["content"]
    content = content.lstrip(replacer[1]).rstrip(replacer[2]).strip("\n")

    return content
