import streamlit as st

st.set_page_config(
    "Compare Sheets",
    layout="wide",
)

from app.app import run_streamlit_app  # noqa: E402

if __name__ == "__main__":
    run_streamlit_app()
