from io import BytesIO
import base64

from pdf2image import convert_from_bytes


def process_file(byte_data, file_type):
    estimator_dict = {
        "pdf": process_pdf,
    }

    estimator = estimator_dict[file_type]
    data = estimator(byte_data)

    return data


def process_pdf(byte_data):
    pdf_imgs = convert_from_bytes(byte_data)
    pdf_base64 = []
    for img in pdf_imgs:
        buffered = BytesIO()
        img.save(buffered, format="JPEG")
        pdf_base64.append(base64.b64encode(buffered.getvalue()).decode())

    return pdf_base64
