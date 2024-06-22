import time
import json
import requests

import streamlit as st
import streamlit_ace as st_ace
from streamlit_lottie import st_lottie_spinner

from config import API_PDF, API_STATUS, ANIM_PATH


st.set_page_config(page_title="DeepScriptum", page_icon="📘", layout="wide")

st.title("📘 :violet[Deep]Scriptum")

st.header(
    "This is DeepScriptum demo page, showing the "
    "capabilities of modern VLLMs to perform "
    "end2end OCR over any document"
)

st.divider()

st.subheader("Use fields below to perform doc recogniton!")

result_format = st.radio("Choose output format:", ("md", "latex"), key="result_format")

uploaded_files = st.file_uploader(
    "Drag PDF file or images here (PNG, JPG)",
    type=["pdf", "png", "jpg"],
    accept_multiple_files=True,
    help="You can upload PDF or images (PNG, JPG)",
    key="uploaded_files",
)


def valid_files(files):
    if len(files) == 1 and files[0].type == "application/pdf":
        return True
    elif all(file.type in ["image/png", "image/jpeg"] for file in files):
        # TODO it should be possible
        return False
    else:
        return False


if uploaded_files and not valid_files(uploaded_files):
    st.error("For now only PDFs are available to upload")


def load_lottiefile(filepath: str):
    with open(filepath, "r") as f:
        return json.load(f)


lottie_spinner = load_lottiefile(ANIM_PATH)

if "s" not in st.session_state:
    st.session_state.s = requests.Session()


if uploaded_files and valid_files(uploaded_files) and st.button("OCR this!"):
    files = [("pdf_file", (file.name, file, file.type)) for file in uploaded_files]
    r = st.session_state.s.post(
        url=API_PDF, data={"decode_type": result_format}, files=files
    )

    if r.status_code == 201:
        with st_lottie_spinner(lottie_spinner, height=600, width=600):
            status_response = -1
            while status_response != 200:
                status_response = st.session_state.s.get(API_STATUS)
                if status_response.status_code == 200:
                    st.session_state.md = status_response.json()["content"]
                    break
                time.sleep(2)
    else:
        raise Exception("Can't send data")

if "md" in st.session_state:
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.md = st_ace.st_ace(
            value=st.session_state.md,
            language="markdown" if result_format == "md" else "latex",
            theme="chrome",
            key="editor",
            height="700px",
            wrap=True,
        )

    with col2:
        custom_html = f"""
            <div style="height: 707px; overflow-y: auto; border: 1px solid #ccc; padding: 10px;">
            {st.session_state.md}
            </div>
            """
        st.write(custom_html, unsafe_allow_html=True)

    st.download_button(
        "Download edited file", st.session_state.md, file_name=f"file.{result_format}"
    )
