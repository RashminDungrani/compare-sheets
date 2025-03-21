from io import BytesIO
from time import perf_counter
from typing import Any

import numpy as np
import pandas as pd


def compare_values(val1: Any, val2: Any) -> bool:
    """Compare two values based on their data types"""
    if pd.isna(val1) and pd.isna(val2):
        return True
    elif pd.isna(val1) or pd.isna(val2):
        return False

    # For float values, compare only first 2 decimal places
    if isinstance(val1, (float, int)) and isinstance(val2, (float, int)):
        return round(float(val1), 2) == round(float(val2), 2)

    # For string values, compare case-insensitive
    if isinstance(val1, str) and isinstance(val2, str):
        return val1.strip().lower() == val2.strip().lower()

    # For other types, direct comparison
    return val1 == val2


def compare_files(df1: pd.DataFrame, df2: pd.DataFrame, column_mapping: dict) -> dict:
    """Compare files and return comparison results"""
    start_time = perf_counter()

    # Extract ID columns
    id_mapping = column_mapping["id"]
    df1_id_col, df2_id_col = id_mapping

    # Convert ID columns to string and ensure they're stripped
    df1[df1_id_col] = df1[df1_id_col].astype(str).str.strip()
    df2[df2_id_col] = df2[df2_id_col].astype(str).str.strip()

    # Find records in df2 but not in df1
    not_in_df1 = df2[~df2[df2_id_col].isin(df1[df1_id_col])]
    print(f"Records in File 2 but not in File 1: {len(not_in_df1)}")

    # Find records in df1 but not in df2
    not_in_df2 = df1[~df1[df1_id_col].isin(df2[df2_id_col])]
    print(f"Records in File 1 but not in File 2: {len(not_in_df2)}")

    # Rename columns to avoid conflicts before merge
    df1_renamed = df1.copy()
    df2_renamed = df2.copy()

    # Create mapping of original to renamed columns
    df1_column_map = {col: f"{col}_file1" for col in df1.columns}
    df2_column_map = {col: f"{col}_file2" for col in df2.columns}

    df1_renamed = df1_renamed.rename(columns=df1_column_map)
    df2_renamed = df2_renamed.rename(columns=df2_column_map)

    # Compare common records using merge with renamed columns
    common_records = pd.merge(
        df1_renamed,
        df2_renamed,
        left_on=f"{df1_id_col}_file1",
        right_on=f"{df2_id_col}_file2",
        how="inner",
    )

    # Initialize comparison data with the ID column
    comparison_data = {"id": common_records[f"{df1_id_col}_file1"].copy()}
    all_matches = np.ones(len(common_records), dtype=bool)

    # Compare each column pair using renamed columns
    for col_name, (col1, col2) in column_mapping.items():
        if col_name == "id":
            continue

        try:
            col1_renamed = f"{col1}_file1"
            col2_renamed = f"{col2}_file2"

            # Verify columns exist before accessing
            if col1_renamed not in common_records.columns:
                raise KeyError(f"Column '{col1}' not found in first file")
            if col2_renamed not in common_records.columns:
                raise KeyError(f"Column '{col2}' not found in second file")

            file1_values = common_records[col1_renamed].values
            file2_values = common_records[col2_renamed].values

            # Compare values using vectorized operations where possible
            matches = np.array(
                [compare_values(v1, v2) for v1, v2 in zip(file1_values, file2_values)],
                dtype=bool,
            )
            all_matches &= matches

            comparison_data.update(
                {
                    f"{col_name}_file1": pd.Series(file1_values),
                    f"{col_name}_file2": pd.Series(file2_values),
                    f"{col_name}_matches": pd.Series(matches),
                }
            )
        except KeyError as e:
            print(f"Warning: Column access error - {e}")
            print(
                f"Available columns in merged dataframe: {common_records.columns.tolist()}"
            )
            raise Exception(
                f"Column '{str(e)}' not found. Please check your column mapping."
            )

    comparison_data["all_columns_match"] = pd.Series(all_matches)
    comparison_df = pd.DataFrame(comparison_data).sort_values(
        "all_columns_match", ascending=False
    )

    # Create summary
    summary = {
        "Total rows in File 1": len(df1),
        "Total rows in File 2": len(df2),
        "Records only in File 1": len(not_in_df2),
        "Records only in File 2": len(not_in_df1),
        "Common records": len(common_records),
        "Matching records": all_matches.sum(),
        "Mismatched records": len(all_matches) - all_matches.sum(),
        "Time taken": f"{perf_counter() - start_time:.2f} seconds",
    }

    return {
        "comparison_df": comparison_df,
        "summary": summary,
        "not_in_file1": not_in_df1,
        "not_in_file2": not_in_df2,
    }


def read_file_preview(file) -> pd.DataFrame:
    """Read first 10 rows of file for preview"""
    if file.name.endswith(".csv"):
        return pd.read_csv(file, nrows=10, header=None)
    return pd.read_excel(file, nrows=10, header=None)


def load_dataframes(
    file1, file2, header1: int, header2: int
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load full dataframes with specified headers"""
    try:
        if file1.name.endswith(".csv"):
            df1 = pd.read_csv(file1, header=header1)
        else:
            df1 = pd.read_excel(file1, header=header1)

        if file2.name.endswith(".csv"):
            df2 = pd.read_csv(file2, header=header2)
        else:
            df2 = pd.read_excel(file2, header=header2)

        # Convert ID columns to string type for consistent comparison
        df1 = df1.astype(str)
        df2 = df2.astype(str)

        return df1, df2
    except Exception as e:
        raise Exception(f"Error loading files: {str(e)}")


class ComparisonSteps:
    UPLOAD = 0
    HEADER = 1
    COLUMN_SELECTION = 2
    COMPARISON = 3


def get_step_status(state_dict):
    """Return current step status for validation"""
    return {
        ComparisonSteps.UPLOAD: bool(
            state_dict.get("file1") and state_dict.get("file2")
        ),
        ComparisonSteps.HEADER: bool(
            state_dict.get("header1") is not None
            and state_dict.get("header2") is not None
        ),
        ComparisonSteps.COLUMN_SELECTION: bool(
            state_dict.get("ref_col1")
            and state_dict.get("ref_col2")
            and state_dict.get("column_pairs")
        ),
        ComparisonSteps.COMPARISON: bool(state_dict.get("comparison_results")),
    }


def export_comparison_to_excel(comparison_results: dict):
    """Export comparison results to a single Excel file"""
    output = BytesIO()
    with pd.ExcelWriter(output) as writer:
        # Write summary
        pd.DataFrame([comparison_results["summary"]]).T.to_excel(
            writer, sheet_name="Summary"
        )

        # Write detailed comparison
        if comparison_results["comparison_df"] is not None:
            comparison_results["comparison_df"].to_excel(
                writer, sheet_name="Detailed Comparison", index=False
            )

        # Write records only in file 1
        if comparison_results["not_in_file2"] is not None:
            comparison_results["not_in_file2"].to_excel(
                writer, sheet_name="Only in File 1", index=False
            )

        # Write records only in file 2
        if comparison_results["not_in_file1"] is not None:
            comparison_results["not_in_file1"].to_excel(
                writer, sheet_name="Only in File 2", index=False
            )

    return output.getvalue()
