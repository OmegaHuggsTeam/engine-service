"""Base resource class with shared HTTP helpers."""

from __future__ import annotations

from typing import Any

import httpx

from ..exceptions import (
    AuthenticationError,
    ConnectionError,
    EngineError,
    NotFoundError,
    ServerError,
    TimeoutError,
    ValidationError,
)


class BaseResource:
    """Base class for all API resource groups.

    Provides ``_get``, ``_post``, ``_put``, ``_delete``, and ``_upload``
    helpers that handle error mapping, so individual resources only deal
    with business logic.
    """

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    # -- helpers -------------------------------------------------------------

    def _raise_for_status(self, response: httpx.Response) -> None:
        """Map HTTP status codes to typed SDK exceptions."""
        code = response.status_code
        if 200 <= code < 300:
            return

        try:
            body = response.json()
        except Exception:
            body = response.text

        if code in (401, 403):
            raise AuthenticationError(
                f"Authentication failed ({code})",
                status_code=code,
                body=body,
            )
        if code == 404:
            raise NotFoundError(
                f"Resource not found ({code})",
                status_code=code,
                body=body,
            )
        if code == 422:
            raise ValidationError(
                f"Validation error ({code})",
                status_code=code,
                body=body,
            )
        if code >= 500:
            raise ServerError(
                f"Server error ({code})",
                status_code=code,
                body=body,
            )
        raise EngineError(
            f"HTTP {code}",
            status_code=code,
            body=body,
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any | None = None,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        files: Any | None = None,
    ) -> Any:
        """Execute an HTTP request and return parsed JSON."""
        try:
            response = await self._client.request(
                method,
                path,
                json=json,
                params=params,
                data=data,
                files=files,
            )
        except httpx.ConnectError as exc:
            raise ConnectionError(
                f"Failed to connect to Engine Service: {exc}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise TimeoutError(
                f"Request timed out: {exc}"
            ) from exc

        self._raise_for_status(response)

        if response.status_code == 204:
            return None

        return response.json()

    async def _get(
        self, path: str, *, params: dict[str, Any] | None = None
    ) -> Any:
        """HTTP GET request."""
        return await self._request("GET", path, params=params)

    async def _post(
        self,
        path: str,
        *,
        json: Any | None = None,
        data: dict[str, Any] | None = None,
        files: Any | None = None,
    ) -> Any:
        """HTTP POST request."""
        return await self._request(
            "POST", path, json=json, data=data, files=files
        )

    async def _put(self, path: str, *, json: Any | None = None) -> Any:
        """HTTP PUT request."""
        return await self._request("PUT", path, json=json)

    async def _delete(self, path: str) -> Any:
        """HTTP DELETE request."""
        return await self._request("DELETE", path)
