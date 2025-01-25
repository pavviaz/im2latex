import magic

from domain.exceptions import BaseAPIException


def process_file(byte_data):
    file_type = detect_file_type(byte_data)
    if file_type == "unknown" or file_type != "pdf":
        raise BaseAPIException(status_code=400, detail="Unsupported format")

    return file_type


def detect_file_type(byte_data):
    mime = magic.Magic(mime=True)
    mime_types = {
        "application/pdf": "pdf",
    }
    return mime_types.get(mime.from_buffer(byte_data), "unknown")
