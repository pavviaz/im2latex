import time
import json
import requests

import streamlit as st
import streamlit_ace as st_ace
from streamlit_lottie import st_lottie


API_PDF = "http://127.0.0.1:8000/pdf"
API_STATUS = "http://127.0.0.1:8000/status"


st.set_page_config(page_title="Загрузка файлов и редактор", page_icon="📄")

# Custom CSS for styling
st.markdown(
    """
    <style>
    .upload-area {
        border: 2px dashed #cccccc;
        padding: 20px;
        text-align: center;
        transition: background-color 0.3s ease;
    }
    .upload-area:hover {
        background-color: #f0f0f0;
    }
    .status-message {
        font-size: 1.2em;
        margin-top: 20px;
    }
    .editor-container {
        margin-top: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Загрузка файлов и редактор")

# Выбор формата результата
result_format = st.radio("Выберите формат результата:", ("md", "latex"))

# Единое поле для загрузки PDF и изображений
uploaded_files = st.file_uploader(
    "Перетащите сюда PDF или изображения (PNG, JPG)",
    type=["pdf", "png", "jpg"],
    accept_multiple_files=True,
    help="Вы можете загрузить PDF или изображения (PNG, JPG)",
)


# Проверка корректности загрузки файлов
def valid_files(files):
    if len(files) == 1 and files[0].type == "application/pdf":
        return True
    elif all(file.type in ["image/png", "image/jpeg"] for file in files):
        return True
    else:
        return False


if uploaded_files and not valid_files(uploaded_files):
    st.error(
        "Вы можете загрузить либо один PDF файл, либо несколько изображений (PNG, JPG)."
    )


# Функция для загрузки Lottie-анимаций из URL или локального файла
def load_lottiefile(filepath: str):
    with open(filepath, "r") as f:
        return json.load(f)


# Загрузка Lottie-анимации
lottie_spinner = load_lottiefile("static/lottie_anim.json")

if "s" not in st.session_state:
    st.session_state.s = requests.Session()

# Кнопка для отправки файлов
if uploaded_files and valid_files(uploaded_files) and st.button("Отправить на сервер"):
    files = [("pdf_file", (file.name, file, file.type)) for file in uploaded_files]
    r = st.session_state.s.post(
        url=API_PDF, data={"decode_type": result_format}, files=files
    )

    if r.status_code == 201:
        st.success("Файлы успешно загружены. Ожидание завершения обработки...")

        # Отображение Lottie-анимации
        with st.echo():
            st_lottie(lottie_spinner, height=600, width=600)
            # Проверка статуса задачи
            status_response = -1
            while status_response != 200:
                status_response = st.session_state.s.get(API_STATUS)
                status = status_response.json().get("msg")
                if status_response.status_code == 200:
                    st.success(status)
                    break
                # elif status_response.status_code == 202:
                #     st.warning(status)
                # elif status_response.status_code == 500:
                #     st.error(status)
                time.sleep(2)

        # Редактор текста
        edited_text = st_ace.st_ace(
            value=status_response.json()["content"],
            language="text",
            theme="monokai",
            key="editor",
        )

        # Сохранение отредактированного текста
        if st.button("Сохранить отредактированный текст"):
            with open("edited_text.txt", "w") as f:
                f.write(edited_text)
            st.success("Текст сохранен успешно!")
    else:
        st.error(f"Ошибка при загрузке файлов")
