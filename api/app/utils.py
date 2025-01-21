import magic
import re
from docx import Document
import mammoth
from io import BytesIO
import pandas as pd
from pdf2image import convert_from_bytes
import base64

async def process_file(byte_data):
    estimator_dict = {
        "pdf": process_pdf,
        "docx": process_docx,
        "doc": process_doc,
        "txt": process_txt,
        "xlsx": process_xlsx
    }
    file_type = await detect_file_type(byte_data)
    if file_type == "unknown":
        return ""
    estimator = estimator_dict[file_type]
    data = await estimator(byte_data)

    return file_type, data

async def detect_file_type(byte_data):
    mime = magic.Magic(mime=True)
    mime_types = {
        "application/pdf": "pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "application/msword": "doc",
        "text/plain": "txt",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx"
    }
    return mime_types.get(mime.from_buffer(byte_data), "unknown")

async def extract_text_from_docx(docx_bytes):
    doc = Document(docx_bytes)
    full_text = []
    for paragraph in doc.paragraphs:
        full_text.append(paragraph.text)
    return '\n'.join(full_text)

async def extract_text_from_doc(doc_bytes):
    result = mammoth.extract_raw_text(doc_bytes)
    return result.value

async def process_text(text, max_length=3000):
    parts = []
    current_part = []
    current_length = 0

    for word in re.split(r'(\s+|\W)', text):
        if current_length + len(word) > max_length:
            parts.append(''.join(current_part))
            current_part = []
            current_length = 0
        current_part.append(word)
        current_length += len(word)
    if current_part:
        parts.append(''.join(current_part))
    return parts

async def process_doc(byte_data):
    text = await extract_text_from_doc(byte_data)
    return await process_text(text)

async def process_docx(byte_data):
    text = await extract_text_from_docx(byte_data)
    return await process_text(text)

async def process_txt(byte_data):
    text = byte_data.decode('utf-8')
    return await process_text(text)

async def process_xlsx(byte_data, max_length = 8000):
    file_stream = BytesIO(byte_data)
    df_str = pd.read_excel(file_stream).to_string()
    str_list = [df_str[i:i + max_length] for i in range(0, len(df_str), max_length)]
    return str_list

async def process_pdf(byte_data):
    pdf_imgs = convert_from_bytes(byte_data)
    pdf_base64 = []
    for img in pdf_imgs:
        buffered = BytesIO()
        img.save(buffered, format="JPEG")
        pdf_base64.append(base64.b64encode(buffered.getvalue()).decode())
    
    return pdf_base64