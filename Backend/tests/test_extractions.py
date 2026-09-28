import io
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.api.routes import extractions
from app.core.config import Settings
from app.main import create_app
from app.schemas.invoice import Invoice
from app.services import documents
from app.services.documents import UnsupportedDocumentError, detect_document_type
from app.services.extraction import InvoiceExtractor


class FakeModel:
    model = "fake-model"

    def __init__(self) -> None:
        self.ocr_text = ""

    def extract_invoice(self, images: list[Image.Image], ocr_text: str) -> Invoice:
        self.ocr_text = ocr_text
        return Invoice(vendor_name="Acme", invoice_number="INV-1", invoice_date="2026-01-05", total_amount="10")


def _png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (20, 20), "white").save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    settings = Settings(_env_file=None, extraction_enabled=True, max_upload_bytes=1024 * 1024)
    monkeypatch.setattr(extractions, "get_settings", lambda: settings)
    # Tesseract is not needed to test the request flow.
    monkeypatch.setattr(documents.pytesseract, "image_to_string", lambda image: "INVOICE INV-1")
    return settings


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    app = create_app(settings)
    app.dependency_overrides[extractions.get_extractor] = lambda: InvoiceExtractor(settings, FakeModel())
    yield TestClient(app)


def test_detects_type_from_content_not_name() -> None:
    assert detect_document_type(b"%PDF-1.7 ...") == "pdf"
    assert detect_document_type(_png_bytes()) == "png"
    with pytest.raises(UnsupportedDocumentError):
        detect_document_type(b"MZ\x90\x00 an exe renamed to invoice.pdf")


def test_extracts_png(client: TestClient) -> None:
    response = client.post("/api/v1/extractions", files={"file": ("invoice.png", _png_bytes(), "image/png")})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["invoice"]["invoice_number"] == "INV-1"
    assert body["page_count"] == 1
    assert body["model"] == "fake-model"


def test_rejects_unsupported_file(client: TestClient) -> None:
    response = client.post("/api/v1/extractions", files={"file": ("invoice.pdf", b"not really a pdf", "application/pdf")})
    assert response.status_code == 415


def test_rejects_oversized_file(client: TestClient, settings: Settings) -> None:
    data = b"%PDF-" + b"0" * settings.max_upload_bytes
    response = client.post("/api/v1/extractions", files={"file": ("big.pdf", data, "application/pdf")})
    assert response.status_code == 413


def test_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(_env_file=None)
    monkeypatch.setattr(extractions, "get_settings", lambda: settings)
    response = TestClient(create_app(settings)).post(
        "/api/v1/extractions", files={"file": ("invoice.png", _png_bytes(), "image/png")}
    )
    assert response.status_code == 503
