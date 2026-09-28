from typing import Protocol

from PIL import Image

from app.core.config import Settings
from app.schemas.invoice import ExtractionResult, Invoice
from app.services.documents import load_pages
from app.services.validation import validate_invoice


class InvoiceModel(Protocol):
    model: str

    def extract_invoice(self, images: list[Image.Image], ocr_text: str) -> Invoice: ...


class InvoiceExtractor:
    """Document bytes in, validated invoice out: pages -> OCR -> model -> business rules."""

    def __init__(self, settings: Settings, model: InvoiceModel) -> None:
        self._settings = settings
        self._model = model

    def extract(self, data: bytes) -> ExtractionResult:
        pages = load_pages(data, self._settings)
        ocr_text = "\n\n".join(
            f"--- Page {number} ---\n{page.ocr_text}" for number, page in enumerate(pages, start=1)
        )
        invoice = self._model.extract_invoice([page.image for page in pages], ocr_text)
        issues = validate_invoice(invoice)
        status = "needs_review" if any(issue.severity == "error" for issue in issues) else "ok"
        return ExtractionResult(
            status=status, invoice=invoice, issues=issues, page_count=len(pages), model=self._model.model
        )
