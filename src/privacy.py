import os
import re
import uuid

TEMP_FOLDER = "temp"


def _safe_filename(filename):
    filename = os.path.basename(filename)

    filename = re.sub(
        r"[^가-힣a-zA-Z0-9_.-]",
        "_",
        filename
    )

    if not filename.lower().endswith(".pdf"):
        filename = filename + ".pdf"

    return filename


def save_uploaded_file(uploaded_file):
    os.makedirs(TEMP_FOLDER, exist_ok=True)

    safe_name = _safe_filename(uploaded_file.name)

    unique_name = f"{uuid.uuid4().hex}_{safe_name}"

    file_path = os.path.join(TEMP_FOLDER, unique_name)

    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return file_path


def delete_uploaded_file(file_path):
    if file_path is None:
        return False

    if os.path.exists(file_path):
        os.remove(file_path)
        return True

    return False


def file_exists(file_path):
    if file_path is None:
        return False

    return os.path.exists(file_path)