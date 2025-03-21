import base64
import uuid
from datetime import UTC, datetime, timedelta
from io import BytesIO

import streamlit.components.v1 as components


def download_file(
    data: bytes | BytesIO,
    filename: str,
    mime: str = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
) -> None:
    """
    Download a file with optional progress tracking and direct browser download.

    Args:
        data: The file data as bytes or BytesIO
        filename: Name of the file to download
        mime: Mime type of the file
        progress_callback: Optional callback function for progress updates
        show_progress: Whether to show the progress bar
    """

    # Convert BytesIO to bytes if needed
    if isinstance(data, BytesIO):
        file_bytes = data.getvalue()
    else:
        file_bytes = data

    # Generate unique ID for download link
    id_link = f"download_{str(uuid.uuid4())}"

    # Encode file data as base64
    b64 = base64.b64encode(file_bytes).decode()

    # Create HTML component for automatic download
    components.html(
        f"""
        <html><body>
            <a href="data:{mime};base64,{b64}" 
                download="{filename}" 
                id="{id_link}">
            </a>
            <script>
                window.onload = function() {{
                    document.getElementById('{id_link}').click();
                }};
            </script>
        </body></html>
        """,
        height=0,
        width=0,
        scrolling=False,
    )


def get_ist_time_str(utc_time: datetime | None = None) -> str:
    if utc_time is None:
        utc_time = datetime.now(UTC)

    ist_time = utc_time + timedelta(hours=5, minutes=30)
    return ist_time.strftime("%Y_%m_%d_%H_%M_%S")
