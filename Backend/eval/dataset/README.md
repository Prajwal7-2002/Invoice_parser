# Evaluation dataset

Put invoice files here with a matching JSON file holding the correct answers:

```
acme-2026-001.pdf
acme-2026-001.json
```

Example `acme-2026-001.json` (only include fields you want scored):

```json
{
  "vendor_name": "Acme Supplies Pvt Ltd",
  "invoice_number": "INV-2026-001",
  "invoice_date": "2026-09-01",
  "currency": "INR",
  "subtotal": "1000.00",
  "tax_amount": "180.00",
  "total_amount": "1180.00",
  "line_items": [
    {"description": "Widget", "quantity": "2", "unit_price": "500.00", "amount": "1000.00"}
  ]
}
```

Everything in this folder except this README is git-ignored, because real invoices
contain customer and financial data. Keep the dataset somewhere private and shared
(for example a restricted bucket) so the whole team scores against the same files.
