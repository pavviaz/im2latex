import os
from multiprocessing.pool import ThreadPool
from typing import List
from celery import Celery
from openai import OpenAI

import config

client = OpenAI(
    api_key=os.getenv("OPENAI_KEY"),
    base_url=os.getenv("BASE_OPENAI_URL"),
)

celery = Celery(__name__)
celery.conf.broker_url = os.getenv("CELERY_BROKER_URL")
celery.conf.result_backend = os.getenv("CELERY_RESULT_BACKEND")

REPLACERS = {"latex": config.LATEX_REPLACER, "md": config.MD_REPLACER}

@celery.task(
    name="images", bind=True, time_limit=600, soft_time_limit=540, track_started=True
)
def process_images(self, imgs_binary: List[str], decode_type: str):
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
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": config.DEFAULT_MAP_PROMPT.format(
                            idx + 1, replacer[0], replacer[0], replacer[0]
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{img_binary}"},
                    },
                ],
            }
        ],
    }

    try:
        response = client.chat.completions.create(
            model=config.MODEL_NAME,
            messages=payload["messages"],
        )
        content = response.choices[0].message.content
        content = content.lstrip(replacer[1]).rstrip(replacer[2]).strip("\n")
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

    return content

def _apply_reduce_ocr(texts: List[str], decode_type: str, replacer: tuple):
    payload = {
        "model": config.MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": [
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
                ],
            }
        ],
    }

    try:
        response = client.chat.completions.create(
            model=config.MODEL_NAME,
            messages=payload["messages"],
        )
        content = response.choices[0].message.content
        content = content.lstrip(replacer[1]).rstrip(replacer[2]).strip("\n")
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

    return content

@celery.task(
    name="texts", bind=True, time_limit=600, soft_time_limit=540, track_started=True
)
def process_texts(self, texts: List[str], decode_type: str):
    replacer = REPLACERS[decode_type]
    texts_enum = [(idx, text, replacer) for idx, text in enumerate(texts)]

    try:
        with ThreadPool(len(texts_enum)) as thread_pool:
            map_results = thread_pool.starmap(_apply_map_text, texts_enum)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=5)

    reduce_result = _apply_reduce_text(map_results, decode_type, replacer)
    return reduce_result

def _apply_map_text(idx: int, text: str, replacer: tuple):
    payload = {
        "model": config.MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": config.DEFAULT_MAP_PROMPT.format(
                            idx + 1, replacer[0], replacer[0], replacer[0]
                        ),
                    },
                    {
                        "type": "text",
                        "text": text,
                    },
                ],
            }
        ],
    }

    try:
        response = client.chat.completions.create(
            model=config.MODEL_NAME,
            messages=payload["messages"],
        )
        content = response.choices[0].message.content
        content = content.lstrip(replacer[1]).rstrip(replacer[2]).strip("\n")
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

    return content

def _apply_reduce_text(texts: List[str], decode_type: str, replacer: tuple):
    payload = {
        "model": config.MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": [
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
                ],
            }
        ],
    }

    try:
        response = client.chat.completions.create(
            model=config.MODEL_NAME,
            messages=payload["messages"],
        )
        content = response.choices[0].message.content
        content = content.lstrip(replacer[1]).rstrip(replacer[2]).strip("\n")
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

    return content
