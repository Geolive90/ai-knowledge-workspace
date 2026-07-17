from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile


UPLOAD_FOLDER = Path("uploads")

UPLOAD_FOLDER.mkdir(exist_ok=True)


def save_uploaded_file(file: UploadFile) -> tuple[str, str]:
    """
    Save an uploaded file.

    Returns:
        (stored_filename, original_filename)
    """

    original_filename = file.filename
    extension = Path(original_filename).suffix
    stored_filename = f"{uuid4()}{extension}"
    destination = UPLOAD_FOLDER / stored_filename

    with destination.open("wb") as buffer:
        buffer.write(file.file.read())

    return stored_filename, original_filename


def get_file_path(stored_filename: str) -> Path:
    """
    Return the full path of a stored document.
    """

    return UPLOAD_FOLDER / stored_filename


def delete_stored_file(stored_filename: str) -> bool:
    """
    Delete a stored file.

    Returns:
        True if the file existed and was deleted.
        False if the file did not exist.
    """

    file_path = get_file_path(stored_filename)

    if not file_path.exists():
        return False

    file_path.unlink()
    return True