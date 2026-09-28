import json

import httpx
import pytest
from PIL import Image

from app.core.config import Settings
from app.services import llm
from app.services.llm import ExtractionError, OpenRouterClient

VALID_REPLY = {"vendor_name": "Acme", "invoice_number": "INV-1", "total_amount": "10.00"}


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(llm.time, "sleep", lambda _: None)


def _completion(content: str) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


def _client(responses: list[httpx.Response]) -> tuple[OpenRouterClient, list[httpx.Request]]:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return responses.pop(0)

    settings = Settings(_env_file=None, openrouter_api_key="test-key", llm_max_attempts=3)
    return OpenRouterClient(settings, httpx.Client(transport=httpx.MockTransport(handler))), requests


def _extract(client: OpenRouterClient):
    return client.extract_invoice([Image.new("RGB", (10, 10))], "ocr text")


def test_parses_fenced_json_reply() -> None:
    client, requests = _client([_completion("```json\n" + json.dumps(VALID_REPLY) + "\n```")])
    invoice = _extract(client)
    assert invoice.invoice_number == "INV-1"
    assert requests[0].headers["Authorization"] == "Bearer test-key"


def test_retries_with_errors_when_reply_is_invalid() -> None:
    client, requests = _client([_completion('{"invoice_date": "last tuesday"}'), _completion(json.dumps(VALID_REPLY))])
    assert _extract(client).vendor_name == "Acme"
    retry_messages = json.loads(requests[1].content)["messages"]
    assert "invoice_date" in retry_messages[-1]["content"]


def test_retries_on_server_error() -> None:
    client, requests = _client([httpx.Response(503), _completion(json.dumps(VALID_REPLY))])
    assert _extract(client).total_amount is not None
    assert len(requests) == 2


def test_gives_up_after_max_attempts() -> None:
    client, _ = _client([httpx.Response(503)] * 3)
    with pytest.raises(ExtractionError, match="unavailable"):
        _extract(client)


def test_out_of_credits_is_not_retried() -> None:
    client, requests = _client([httpx.Response(402, json={"error": {"message": "More credits are required"}})])
    with pytest.raises(ExtractionError, match="credits"):
        _extract(client)
    assert len(requests) == 1


def test_missing_api_key_is_rejected() -> None:
    with pytest.raises(ExtractionError):
        OpenRouterClient(Settings(_env_file=None))
