"""Shared test fixtures for Engine SDK tests."""

from __future__ import annotations

import pytest
import httpx

from engine_sdk.client import EngineClient


@pytest.fixture
def mock_transport():
    """Create a mock httpx transport that returns configurable responses."""
    return MockTransport()


@pytest.fixture
async def client(mock_transport):
    """Create an EngineClient with a mocked transport."""
    http_client = httpx.AsyncClient(
        base_url="http://test-engine:8766",
        transport=mock_transport,
    )
    engine_client = EngineClient(httpx_client=http_client)
    yield engine_client
    await engine_client.close()


class MockTransport(httpx.AsyncBaseTransport):
    """Configurable mock transport for testing.

    Set ``self.responses`` to a list of ``(status_code, json_body)``
    tuples. Responses are consumed in order; if exhausted, the last
    response is reused.
    """

    def __init__(self) -> None:
        self.responses: list[tuple[int, dict | list | str]] = [
            (200, {})
        ]
        self.requests: list[httpx.Request] = []
        self._index = 0

    def set_response(
        self, status_code: int = 200, body: dict | list | str | None = None
    ) -> None:
        """Set a single response."""
        self.responses = [(status_code, body or {})]
        self._index = 0

    def set_responses(
        self, *responses: tuple[int, dict | list | str]
    ) -> None:
        """Set multiple responses to be consumed in order."""
        self.responses = list(responses)
        self._index = 0

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)

        if self._index < len(self.responses):
            status_code, body = self.responses[self._index]
            self._index += 1
        else:
            # Reuse last response
            status_code, body = self.responses[-1]

        import json
        if isinstance(body, (dict, list)):
            content = json.dumps(body).encode()
            headers = {"content-type": "application/json"}
        else:
            content = str(body).encode()
            headers = {"content-type": "text/plain"}

        return httpx.Response(
            status_code=status_code,
            headers=headers,
            content=content,
            request=request,
        )

    @property
    def last_request(self) -> httpx.Request | None:
        return self.requests[-1] if self.requests else None
