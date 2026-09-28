"""Turn an uploaded file into page images and OCR text.

The file type is decided from its leading bytes, never from the client's
filename or Content-Type, so a renamed file cannot slip through.
"""

import io
import logging
from dataclasses import dataclass
from typing import Literal

import pytesseract
from pdf2image import convert_from_bytes
from pdf2image.exceptions import PDFPageCountError, PDFSyntaxError
from PIL import Image, UnidentifiedImageError

from app.core.config import Settings

logger = logging.getLogger(__name__)

DocumentType = Literal["pdf", "png", "jpeg"]

_SIGNATURES: tuple[tuple[bytes, DocumentType], ...] = (
    (b"%PDF-", "pdf"),
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"\xff\xd8\xff", "jpeg"),
)


class DocumentError(Exception):
    """The uploaded file cannot be processed; the message is safe to show to the client."""


class UnsupportedDocumentError(DocumentError):
    pass


class TooManyPagesError(DocumentError):
    pass


@dataclass
class Page:
    image: Image.Image
    ocr_text: str


def detect_document_type(data: bytes) -> DocumentType:
    for signature, document_type in _SIGNATURES:
        if data.startswith(signature):
            return document_type
    raise UnsupportedDocumentError("Only PDF, PNG and JPEG files are supported.")


def _render_pages(data: bytes, document_type: DocumentType, settings: Settings) -> list[Image.Image]:
    if document_type == "pdf":
        try:
            # Render one page past the limit so an oversized PDF is rejected, not truncated.
            images = convert_from_bytes(
                data, dpi=200, first_page=1, last_page=settings.max_pages + 1, poppler_path=settings.poppler_path
            )
        except (PDFPageCountError, PDFSyntaxError) as exc:
            raise UnsupportedDocumentError("The PDF could not be read.") from exc
        if len(images) > settings.max_pages:
            raise TooManyPagesError(f"Documents are limited to {settings.max_pages} pages.")
        return images

    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise UnsupportedDocumentError("The image could not be read.") from exc
    return [image]


def _normalise(image: Image.Image, max_side: int) -> Image.Image:
    image = image.convert("RGB")
    image.thumbnail((max_side, max_side))
    return image


def load_pages(data: bytes, settings: Settings) -> list[Page]:
    if settings.tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd

    document_type = detect_document_type(data)
    pages = []
    for image in _render_pages(data, document_type, settings):
        image = _normalise(image, settings.max_image_side)
        pages.append(Page(image=image, ocr_text=pytesseract.image_to_string(image).strip()))
    logger.info("Loaded %s document with %d page(s)", document_type, len(pages))
    return pages
