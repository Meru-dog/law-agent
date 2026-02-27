"""Text extraction utilities for PDF and DOCX documents.

Extracts text with anchors (page numbers for PDF, paragraph IDs for DOCX)
to enable precise citation in answers.
"""

from pathlib import Path
from typing import NamedTuple

try:
    import pypdf
except ImportError:
    pypdf = None

try:
    import docx
except ImportError:
    docx = None


class Anchor(NamedTuple):
    """Represents a text anchor in a document."""

    anchor_type: str
    anchor_value: str
    text_content: str


class ExtractionResult(NamedTuple):
    """Result of text extraction with anchors."""

    doc_type: str
    anchors: list[Anchor]


def extract_text_from_pdf(file_path: Path) -> ExtractionResult:
    """Extract text from PDF with page anchors.

    Args:
        file_path: Path to the PDF file.

    Returns:
        ExtractionResult with page-level anchors.

    Raises:
        ImportError: If pypdf is not installed.
        ValueError: If the file cannot be read.
    """
    if pypdf is None:
        raise ImportError("pypdf is required for PDF extraction. Install with: pip install pypdf")

    try:
        reader = pypdf.PdfReader(file_path)
        anchors = []

        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text()
            if text.strip():
                anchors.append(
                    Anchor(
                        anchor_type="page",
                        anchor_value=str(page_num),
                        text_content=text,
                    )
                )

        return ExtractionResult(doc_type="pdf", anchors=anchors)
    except Exception as e:
        raise ValueError(f"Failed to extract text from PDF: {e}") from e


def extract_text_from_docx(file_path: Path) -> ExtractionResult:
    """Extract text from DOCX with paragraph anchors.

    Args:
        file_path: Path to the DOCX file.

    Returns:
        ExtractionResult with paragraph-level anchors.

    Raises:
        ImportError: If python-docx is not installed.
        ValueError: If the file cannot be read.
    """
    if docx is None:
        raise ImportError(
            "python-docx is required for DOCX extraction. Install with: pip install python-docx"
        )

    try:
        doc = docx.Document(file_path)
        anchors = []

        for para_num, paragraph in enumerate(doc.paragraphs, start=1):
            text = paragraph.text
            if text.strip():
                anchors.append(
                    Anchor(
                        anchor_type="paragraph",
                        anchor_value=str(para_num),
                        text_content=text,
                    )
                )

        return ExtractionResult(doc_type="docx", anchors=anchors)
    except Exception as e:
        raise ValueError(f"Failed to extract text from DOCX: {e}") from e


def extract_text(file_path: Path) -> ExtractionResult:
    """Extract text from a document based on file extension.

    Args:
        file_path: Path to the document.

    Returns:
        ExtractionResult with anchors appropriate for the document type.

    Raises:
        ValueError: If file type is unsupported or extraction fails.
    """
    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        return extract_text_from_pdf(file_path)
    elif suffix in [".docx", ".doc"]:
        return extract_text_from_docx(file_path)
    else:
        raise ValueError(f"Unsupported file type: {suffix}. Supported types: .pdf, .docx")
