import pandas as pd
import streamlit as st

from app.pages.sheets.state import (
    ComparisonSteps,
    compare_files,
    export_comparison_to_excel,
    load_dataframes,
    read_file_preview,
)
from app.pages.utils import download_file, get_ist_time_str


### File Comparison
@st.fragment
def render_file_comparison():
    def display_progress(current_step):
        steps = ["Upload Files", "Select Headers", "Column Selection", "View Results"]
        st.progress(current_step / (len(steps) - 1))
        st.subheader(f"Step {current_step + 1}: {steps[current_step]}")

    def handle_file_upload():
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.file1 = st.file_uploader(
                "Upload first file", type=["xlsx"]
            )
        with col2:
            st.session_state.file2 = st.file_uploader(
                "Upload second file", type=["xlsx"]
            )

        if st.session_state.file1 and st.session_state.file2:
            st.success("✅ Both files uploaded successfully!")
            st.button(
                "Next →",
                on_click=lambda: setattr(
                    st.session_state, "current_step", ComparisonSteps.HEADER
                ),
                type="primary",
            )
        else:
            st.warning("⚠️ Please upload both Excel files to continue")

    def handle_header_selection():
        try:
            df1_preview = read_file_preview(st.session_state.file1)
            df2_preview = read_file_preview(st.session_state.file2)

            col1, col2 = st.columns(2)
            with col1:
                st.write("File 1 Preview:")
                st.dataframe(df1_preview.head(10), height=200)
                st.session_state.header1 = st.number_input(
                    "Header row for File 1", 0, 9, 0
                )
            with col2:
                st.write("File 2 Preview:")
                st.dataframe(df2_preview.head(10), height=200)
                st.session_state.header2 = st.number_input(
                    "Header row for File 2", 0, 9, 0
                )

            col1, col2 = st.columns([1, 4])
            with col1:
                st.button(
                    "← Back",
                    on_click=lambda: setattr(
                        st.session_state, "current_step", ComparisonSteps.UPLOAD
                    ),
                )
            with col2:
                st.button(
                    "Next →",
                    on_click=lambda: setattr(
                        st.session_state,
                        "current_step",
                        ComparisonSteps.COLUMN_SELECTION,
                    ),
                    type="primary",
                )

        except Exception as e:
            st.error(f"Error loading files: {str(e)}")

    def read_dataframes() -> tuple[pd.DataFrame, pd.DataFrame]:
        df1, df2 = load_dataframes(
            st.session_state.file1,
            st.session_state.file2,
            st.session_state.header1,
            st.session_state.header2,
        )
        return df1, df2

    @st.fragment
    def handle_column_selection(df1: pd.DataFrame, df2: pd.DataFrame):
        try:
            st.info("🔍 Select the columns to compare between the files")

            # Reference column selection
            col1, col2 = st.columns(2)
            with col1:
                st.session_state.ref_col1 = st.selectbox(
                    "ID column from File 1", df1.columns
                )
            with col2:
                st.session_state.ref_col2 = st.selectbox(
                    "ID column from File 2", df2.columns
                )

            # Comparison columns
            st.divider()
            st.subheader("Columns to Compare")
            num_comparisons = st.number_input("Number of column pairs", 1, 10, 1)

            column_pairs = []
            for i in range(num_comparisons):
                col1, col2 = st.columns(2)
                with col1:
                    comp_col1 = st.selectbox(
                        f"Column from File 1 #{i + 1}", df1.columns
                    )
                with col2:
                    comp_col2 = st.selectbox(
                        f"Column from File 2 #{i + 1}", df2.columns
                    )
                column_pairs.append((comp_col1, comp_col2))

            st.session_state.column_pairs = column_pairs

            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button(
                    "← Back",
                    on_click=lambda: setattr(
                        st.session_state, "current_step", ComparisonSteps.HEADER
                    ),
                ):
                    st.rerun()

            with col2:
                if (
                    st.session_state.ref_col1
                    and st.session_state.ref_col2
                    and column_pairs
                ):
                    if st.button(
                        "Compare Files →",
                        on_click=lambda: setattr(
                            st.session_state, "current_step", ComparisonSteps.COMPARISON
                        ),
                        type="primary",
                    ):
                        st.rerun()
                else:
                    st.warning("⚠️ Please select all required columns")

        except Exception as e:
            st.error(f"Error loading data: {str(e)}")

    @st.fragment
    def display_comparison_results(results):
        st.subheader("📊 Comparison Summary")
        summary_cols = st.columns(4)
        with summary_cols[0]:
            st.metric("Total in File 1", results["summary"]["Total rows in File 1"])
        with summary_cols[1]:
            st.metric("Total in File 2", results["summary"]["Total rows in File 2"])
        with summary_cols[2]:
            st.metric("Matching Records", results["summary"]["Matching records"])
        with summary_cols[3]:
            st.metric("Mismatched Records", results["summary"]["Mismatched records"])

        if st.button("📥 Download Detailed Report", use_container_width=True):
            # Export button
            excel_data = export_comparison_to_excel(results)
            filename = f"nexus-comparison-report_{get_ist_time_str()}.xlsx"
            download_file(excel_data, filename)

        if st.button(
            "← Start New Comparison",
            on_click=lambda: setattr(
                st.session_state, "current_step", ComparisonSteps.UPLOAD
            ),
        ):
            st.rerun()

    def handle_comparison_results():
        try:
            with st.spinner("Comparing files...", show_time=True):
                df1, df2 = load_dataframes(
                    st.session_state.file1,
                    st.session_state.file2,
                    st.session_state.header1,
                    st.session_state.header2,
                )

                column_mapping = {
                    "id": (st.session_state.ref_col1, st.session_state.ref_col2),
                    **{
                        f"comparison_{i}": pair
                        for i, pair in enumerate(st.session_state.column_pairs)
                    },
                }

                results = compare_files(df1, df2, column_mapping)

                display_comparison_results(results)

        except Exception as e:
            # st.error(f"Error during comparison: {str(e)}")
            raise e
            st.button(
                "← Back",
                on_click=lambda: setattr(
                    st.session_state, "current_step", ComparisonSteps.COLUMN_SELECTION
                ),
            )

    ##
    st.markdown("### File Comparison")

    # Initialize session state
    if "current_step" not in st.session_state:
        st.session_state.current_step = ComparisonSteps.UPLOAD

    display_progress(st.session_state.current_step)

    # Handle different steps
    if st.session_state.current_step == ComparisonSteps.UPLOAD:
        handle_file_upload()
    elif st.session_state.current_step == ComparisonSteps.HEADER:
        handle_header_selection()
    elif st.session_state.current_step == ComparisonSteps.COLUMN_SELECTION:
        with st.spinner("Loading dataframes...", show_time=True):
            df1, df2 = read_dataframes()
        handle_column_selection(df1, df2)
    elif st.session_state.current_step == ComparisonSteps.COMPARISON:
        handle_comparison_results()
