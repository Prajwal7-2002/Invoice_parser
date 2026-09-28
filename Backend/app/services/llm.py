"""Vision-model extraction through OpenRouter's chat completions API."""

import base64
import io
import json
import logging
import time

import httpx
from PIL import Image
from pydantic import ValidationError

from app.core.config import Settings
from app.schemas.invoice import Invoice

logger = logging.getLogger(__name__)

_RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}

SYSTEM_PROMPT = """You extract data from invoices.
Reply with a single JSON object and nothing else. It must match this JSON schema:
{schema}

Rules:
- Use null for any field that is not printed on the invoice. Never guess.
- Dates must be YYYY-MM-DD.
- Amounts must be plain numbers with a '.' decimal separator and no currency symbols or thousands separators.
- currency is the ISO 4217 code (for example INR, USD, EUR).
- tax_amount is the sum of all taxes on the invoice.
- If the document has several pages, they belong to one invoice; return one object."""


class ExtractionError(Exception):
    """The model could not produce a usable result; the message is safe to show to the client."""


def _encode_image(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _strip_code_fence(content: str) -> str:
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1] if "\n" in content else ""
        content = content.rsplit("```", 1)[0]
    return content.strip()


class OpenRouterClient:
    def __init__(self, settings: Settings, http_client: httpx.Client | None = None) -> None:
        if settings.openrouter_api_key is None:
            raise ExtractionError("The extraction model is not configured.")
        self._settings = settings
        self._http = http_client or httpx.Client(timeout=settings.llm_timeout_seconds)
        self._headers = {"Authorization": f"Bearer {settings.openrouter_api_key.get_secret_value()}"}
        self._system_prompt = SYSTEM_PROMPT.format(schema=json.dumps(Invoice.model_json_schema()))

    @property
    def model(self) -> str:
        return self._settings.llm_model

    def extract_invoice(self, images: list[Image.Image], ocr_text: str) -> Invoice:
        user_content: list[dict] = [
            {
                "type": "text",
                "text": (
                    "Extract the invoice in these page images. OCR text is included as a hint; "
                    "trust the images where they disagree.\n\nOCR text:\n" + (ocr_text or "(none)")
                ),
            }
        ]
        user_content += [
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{_encode_image(image)}"}}
            for image in images
        ]
        messages: list[dict] = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": user_content},
        ]

        last_error = ""
        for attempt in range(1, self._settings.llm_max_attempts + 1):
            content = self._complete(messages)
            try:
                return Invoice.model_validate_json(_strip_code_fence(content))
            except ValidationError as exc:
                last_error = str(exc)
                logger.warning("Model reply failed validation (attempt %d): %s", attempt, last_error)
                # Show the model its own reply and the errors so the retry can correct them.
                messages += [
                    {"role": "assistant", "content": content},
                    {
                        "role": "user",
                        "content": f"That reply was not valid. Fix these errors and reply with JSON only:\n{last_error}",
                    },
                ]
        raise ExtractionError("The model did not return a valid invoice after several attempts.")

    def _complete(self, messages: list[dict]) -> str:
        payload = {
            "model": self._settings.llm_model,
            "messages": messages,
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        url = f"{self._settings.openrouter_base_url}/chat/completions"

        for attempt in range(1, self._settings.llm_max_attempts + 1):
            try:
                response = self._http.post(url, headers=self._headers, json=payload)
            except httpx.TransportError as exc:
                logger.warning("Model request failed (attempt %d): %s", attempt, exc)
            else:
                if response.status_code == 200:
                    try:
                        body = response.json()
                        return body["choices"][0]["message"]["content"] or ""
                    except (ValueError, KeyError, IndexError, TypeError) as exc:
                        raise ExtractionError("The model returned an unexpected response.") from exc
                if response.status_code == 402:
                    raise ExtractionError("The model provider account is out of credits.")
                if response.status_code not in _RETRYABLE_STATUS:
                    logger.error("Model request rejected: %s %s", response.status_code, response.text[:500])
                    raise ExtractionError("The model provider rejected the request.")
                logger.warning("Model request returned %s (attempt %d)", response.status_code, attempt)

            if attempt < self._settings.llm_max_attempts:
                time.sleep(2 ** (attempt - 1))
        raise ExtractionError("The model provider is unavailable. Try again later.")
