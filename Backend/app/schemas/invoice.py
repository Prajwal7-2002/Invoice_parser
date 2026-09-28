import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator


def _parse_amount(value: object) -> object:
    """Accept '1,234.50', '$1234.5' or '(12.00)' from the model; leave anything else to Pydantic."""
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text:
        return None
    negative = text.startswith("(") and text.endswith(")")
    cleaned = re.sub(r"[^0-9.\-]", "", text)
    if not cleaned:
        return None
    try:
        amount = Decimal(cleaned)
    except InvalidOperation:
        return value
    return -amount if negative else amount


Amount = Annotated[Decimal | None, BeforeValidator(_parse_amount)]


class LineItem(BaseModel):
    description: str | None = None
    quantity: Amount = None
    unit_price: Amount = None
    amount: Amount = Field(default=None, description="Line total as printed on the invoice.")


class Invoice(BaseModel):
    """Fields extracted from one invoice. Every field is optional; missing ones are reported as issues."""

    model_config = ConfigDict(str_strip_whitespace=True)

    vendor_name: str | None = None
    vendor_tax_id: str | None = Field(default=None, description="GSTIN, VAT or other tax number of the seller.")
    customer_name: str | None = None
    invoice_number: str | None = None
    invoice_date: date | None = Field(default=None, description="ISO 8601 date, YYYY-MM-DD.")
    due_date: date | None = Field(default=None, description="ISO 8601 date, YYYY-MM-DD.")
    currency: str | None = Field(default=None, description="ISO 4217 code such as INR, USD or EUR.")
    subtotal: Amount = Field(default=None, description="Sum of line items before discount, shipping and tax.")
    discount_amount: Amount = None
    shipping_amount: Amount = None
    tax_amount: Amount = Field(default=None, description="Total of all taxes (e.g. CGST + SGST + IGST).")
    total_amount: Amount = Field(default=None, description="Final amount payable.")
    line_items: list[LineItem] = Field(default_factory=list)

    @field_validator("currency")
    @classmethod
    def _normalise_currency(cls, value: str | None) -> str | None:
        return value.upper() if value else value

    @field_validator("line_items", mode="before")
    @classmethod
    def _none_to_empty(cls, value: object) -> object:
        return [] if value is None else value


class ValidationIssue(BaseModel):
    code: str
    severity: Literal["error", "warning"]
    message: str
    field: str | None = None


class ExtractionResult(BaseModel):
    status: Literal["ok", "needs_review"]
    invoice: Invoice
    issues: list[ValidationIssue]
    page_count: int
    model: str
