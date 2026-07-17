from pathlib import Path

from docx import Document
from pypdf import PdfReader


def extract_text(file_path: Path) -> str:
    """
    Extract text from a supported document.

    Supported formats:
    - .txt
    - .docx
    - .pdf
    """

    extension = file_path.suffix.lower()

    if extension == ".txt":
        return extract_txt(file_path)

    if extension == ".docx":
        return extract_docx(file_path)

    if extension == ".pdf":
        return extract_pdf(file_path)

    raise ValueError(f"Unsupported file type: {extension}")


def extract_txt(file_path: Path) -> str:
    """
    Extract text from a text file.
    """
    return file_path.read_text(encoding="utf-8")


def extract_docx(file_path: Path) -> str:
    """
    Extract text from a Microsoft Word document.
    """
    document = Document(file_path)

    paragraphs = [
        paragraph.text
        for paragraph in document.paragraphs
        if paragraph.text.strip()
    ]

    return "\n".join(paragraphs)


def extract_pdf(file_path: Path) -> str:
    """
    Extract text from a PDF document.
    """
    reader = PdfReader(file_path)

    pages = []

    for page in reader.pages:
        text = page.extract_text()

        if text:
            pages.append(text)

    return "\n".join(pages)