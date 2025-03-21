import streamlit as st


def run_streamlit_app():
    try:
        # Main app logic
        from app.pages.sheets.ui import render_file_comparison

        render_file_comparison()

    except Exception as e:
        st.error(f"Application error: {str(e)}")


if __name__ == "__main__":
    run_streamlit_app()
