from datetime import date
from decimal import Decimal

from app.schemas.invoice import Invoice
from app.services.validation import validate_invoice

TODAY = date(2026, 9, 28)


def _valid_invoice(**overrides) -> Invoice:
    data = {
        "vendor_name": "Acme Supplies",
        "invoice_number": "INV-001",
        "invoice_date": "2026-09-01",
        "due_date": "2026-09-30",
        "currency": "inr",
        "subtotal": "1,000.00",
        "tax_amount": "180.00",
        "total_amount": "1180.00",
        "line_items": [
            {"description": "Widget", "quantity": 2, "unit_price": "250", "amount": "500"},
            {"description": "Gadget", "quantity": 1, "unit_price": "500", "amount": "500.00"},
        ],
    }
    data.update(overrides)
    return Invoice.model_validate(data)


def _codes(invoice: Invoice) -> set[str]:
    return {issue.code for issue in validate_invoice(invoice, today=TODAY)}


def test_consistent_invoice_has_no_issues() -> None:
    assert _codes(_valid_invoice()) == set()


def test_amounts_and_currency_are_normalised() -> None:
    invoice = _valid_invoice(total_amount="₹1,180.00", discount_amount="(0.00)")
    assert invoice.total_amount == Decimal("1180.00")
    assert invoice.currency == "INR"


def test_missing_required_fields_are_errors() -> None:
    issues = validate_invoice(_valid_invoice(vendor_name=None, invoice_number=""), today=TODAY)
    missing = {issue.field for issue in issues if issue.code == "missing_field"}
    assert missing == {"vendor_name", "invoice_number"}
    assert all(issue.severity == "error" for issue in issues)


def test_total_mismatch_is_detected() -> None:
    assert "total_mismatch" in _codes(_valid_invoice(total_amount="1200.00"))


def test_discount_and_shipping_are_included_in_total() -> None:
    invoice = _valid_invoice(discount_amount="100", shipping_amount="50", total_amount="1130")
    assert _codes(invoice) == set()


def test_round_off_on_total_is_tolerated() -> None:
    assert _codes(_valid_invoice(tax_amount="180.40", total_amount="1180.00")) == set()


def test_small_mismatch_on_large_total_is_detected() -> None:
    invoice = _valid_invoice(line_items=[], subtotal="1000000", tax_amount="180000", total_amount="1180500")
    assert "total_mismatch" in _codes(invoice)


def test_line_items_mismatch_is_detected() -> None:
    assert "line_items_mismatch" in _codes(_valid_invoice(subtotal="900"))


def test_line_item_math_is_a_warning() -> None:
    items = [{"description": "Widget", "quantity": 3, "unit_price": "250", "amount": "1000"}]
    issues = validate_invoice(_valid_invoice(line_items=items), today=TODAY)
    math = [issue for issue in issues if issue.code == "line_item_math"]
    assert len(math) == 1 and math[0].severity == "warning"


def test_due_date_before_invoice_date_is_error() -> None:
    assert "due_before_invoice_date" in _codes(_valid_invoice(due_date="2026-08-01"))


def test_future_invoice_date_is_warning() -> None:
    assert "future_invoice_date" in _codes(_valid_invoice(invoice_date="2026-12-01", due_date=None))
