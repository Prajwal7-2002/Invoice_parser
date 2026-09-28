"""Business-rule checks on an extracted invoice.

The model can read an invoice wrongly and still return well-formed JSON, so every
result is checked for internal consistency. Any error-level issue sends the
invoice to human review instead of being silently accepted.
"""

import re
from datetime import date
from decimal import Decimal

from app.schemas.invoice import Invoice, ValidationIssue

REQUIRED_FIELDS = ("vendor_name", "invoice_number", "invoice_date", "total_amount")


# Per-line rounding; the difference can grow by a paisa/cent per line summed.
LINE_TOLERANCE = Decimal("0.05")
# Totals are often rounded to the nearest whole unit ("Round off" on Indian invoices).
TOTAL_TOLERANCE = Decimal("1.00")


def _close(actual: Decimal, expected: Decimal, tolerance: Decimal) -> bool:
    return abs(actual - expected) <= tolerance


def validate_invoice(invoice: Invoice, today: date | None = None) -> list[ValidationIssue]:
    today = today or date.today()
    issues: list[ValidationIssue] = []

    for field in REQUIRED_FIELDS:
        if getattr(invoice, field) in (None, ""):
            issues.append(
                ValidationIssue(code="missing_field", severity="error", field=field, message=f"{field} was not found.")
            )

    line_amounts = [item.amount for item in invoice.line_items if item.amount is not None]
    if invoice.subtotal is not None and line_amounts and len(line_amounts) == len(invoice.line_items):
        line_total = sum(line_amounts, Decimal(0))
        tolerance = LINE_TOLERANCE + Decimal("0.01") * len(line_amounts)
        if not _close(line_total, invoice.subtotal, tolerance):
            issues.append(
                ValidationIssue(
                    code="line_items_mismatch",
                    severity="error",
                    field="subtotal",
                    message=f"Line items add up to {line_total}, but the subtotal is {invoice.subtotal}.",
                )
            )

    if invoice.subtotal is not None and invoice.total_amount is not None:
        expected_total = (
            invoice.subtotal
            - (invoice.discount_amount or 0)
            + (invoice.shipping_amount or 0)
            + (invoice.tax_amount or 0)
        )
        if not _close(invoice.total_amount, expected_total, TOTAL_TOLERANCE):
            issues.append(
                ValidationIssue(
                    code="total_mismatch",
                    severity="error",
                    field="total_amount",
                    message=(
                        f"Subtotal - discount + shipping + tax = {expected_total}, "
                        f"but the total is {invoice.total_amount}."
                    ),
                )
            )

    for index, item in enumerate(invoice.line_items):
        if item.quantity is not None and item.unit_price is not None and item.amount is not None:
            expected = item.quantity * item.unit_price
            if not _close(item.amount, expected, LINE_TOLERANCE):
                issues.append(
                    ValidationIssue(
                        code="line_item_math",
                        severity="warning",
                        field=f"line_items[{index}].amount",
                        message=f"Quantity x unit price = {expected}, but the line amount is {item.amount}.",
                    )
                )

    if invoice.invoice_date and invoice.due_date and invoice.due_date < invoice.invoice_date:
        issues.append(
            ValidationIssue(
                code="due_before_invoice_date",
                severity="error",
                field="due_date",
                message="The due date is earlier than the invoice date.",
            )
        )

    if invoice.invoice_date and invoice.invoice_date > today:
        issues.append(
            ValidationIssue(
                code="future_invoice_date",
                severity="warning",
                field="invoice_date",
                message="The invoice date is in the future.",
            )
        )

    if invoice.total_amount is not None and invoice.total_amount < 0:
        issues.append(
            ValidationIssue(
                code="negative_total",
                severity="warning",
                field="total_amount",
                message="The total is negative; this may be a credit note.",
            )
        )

    if invoice.currency and not re.fullmatch(r"[A-Z]{3}", invoice.currency):
        issues.append(
            ValidationIssue(
                code="invalid_currency",
                severity="warning",
                field="currency",
                message=f"'{invoice.currency}' is not an ISO 4217 currency code.",
            )
        )

    return issues
