"""Score the extractor against invoices with known correct answers.

Usage (from Backend/, with OPENROUTER_API_KEY set in .env):
    python -m eval.run_eval
    python -m eval.run_eval --dataset eval/dataset --output eval/results.json

The dataset folder holds pairs: `<name>.pdf|.png|.jpg` and `<name>.json`, where
the JSON is the correct Invoice (see app/schemas/invoice.py). Fields left out of
the expected JSON are not scored.
"""

import argparse
import json
import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from app.core.config import get_settings
from app.schemas.invoice import Invoice
from app.services.extraction import InvoiceExtractor
from app.services.llm import OpenRouterClient

DOCUMENT_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg"}
SCORED_FIELDS = [name for name in Invoice.model_fields if name != "line_items"]


def _normalise_text(value: str) -> str:
    return " ".join(value.lower().split())


def _field_matches(expected: object, actual: object) -> bool:
    if expected is None:
        return actual is None
    if actual is None:
        return False
    if isinstance(expected, Decimal):
        return abs(expected - actual) <= Decimal("0.01")
    if isinstance(expected, str):
        return _normalise_text(expected) == _normalise_text(str(actual))
    return expected == actual


def _line_items_match(expected: Invoice, actual: Invoice) -> bool:
    if len(expected.line_items) != len(actual.line_items):
        return False
    return all(
        _field_matches(want.amount, got.amount) for want, got in zip(expected.line_items, actual.line_items)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset", type=Path, default=Path(__file__).parent / "dataset")
    parser.add_argument("--output", type=Path, default=None, help="Write per-document results as JSON.")
    args = parser.parse_args()

    documents = sorted(path for path in args.dataset.iterdir() if path.suffix.lower() in DOCUMENT_SUFFIXES)
    cases = [(doc, doc.with_suffix(".json")) for doc in documents if doc.with_suffix(".json").exists()]
    if not cases:
        print(f"No document + .json pairs found in {args.dataset}", file=sys.stderr)
        return 1

    settings = get_settings()
    extractor = InvoiceExtractor(settings, OpenRouterClient(settings))

    correct: dict[str, int] = defaultdict(int)
    scored: dict[str, int] = defaultdict(int)
    report = []
    for document, expected_path in cases:
        expected_raw = json.loads(expected_path.read_text(encoding="utf-8"))
        expected = Invoice.model_validate(expected_raw)
        try:
            result = extractor.extract(document.read_bytes())
        except Exception as exc:  # noqa: BLE001 - one bad document must not stop the run
            print(f"FAIL  {document.name}: {exc}")
            report.append({"document": document.name, "error": str(exc)})
            for field in expected_raw:
                scored[field] += 1
            continue

        wrong = []
        for field in expected_raw:
            scored[field] += 1
            if field == "line_items":
                ok = _line_items_match(expected, result.invoice)
            else:
                ok = _field_matches(getattr(expected, field), getattr(result.invoice, field))
            if ok:
                correct[field] += 1
            else:
                wrong.append(field)

        print(f"{'OK  ' if not wrong else 'MISS'}  {document.name}  status={result.status}  wrong={wrong or '-'}")
        report.append(
            {
                "document": document.name,
                "status": result.status,
                "wrong_fields": wrong,
                "issues": [issue.model_dump() for issue in result.issues],
                "extracted": result.invoice.model_dump(mode="json"),
            }
        )

    print(f"\nField accuracy over {len(cases)} document(s):")
    for field in [*SCORED_FIELDS, "line_items"]:
        if scored[field]:
            print(f"  {field:<18} {correct[field] / scored[field]:6.1%}  ({correct[field]}/{scored[field]})")
    overall = sum(correct.values()) / sum(scored.values())
    print(f"  {'overall':<18} {overall:6.1%}")

    if args.output:
        args.output.write_text(json.dumps({"overall": overall, "documents": report}, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
