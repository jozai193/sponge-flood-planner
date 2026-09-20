"""ASGI request-body limits applied before Starlette parses multipart uploads."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

from services.api.settings import settings

ASGIMessage = dict[str, Any]
Receive = Callable[[], Awaitable[ASGIMessage]]
Send = Callable[[ASGIMessage], Awaitable[None]]


class RequestBodyTooLarge(Exception):
    pass


class RequestBodyLimitMiddleware:
    def __init__(self, app):
        self.app = app

    @staticmethod
    def _limit(scope: dict) -> int | None:
        if scope.get("type") != "http" or scope.get("method") not in {"POST", "PUT", "PATCH"}:
            return None
        path = str(scope.get("path", ""))
        if path.endswith("/terrain-import"):
            return settings.max_terrain_request_bytes
        if path.endswith("/imports"):
            return 10_100_000
        return settings.max_request_body_bytes

    async def __call__(self, scope: dict, receive: Receive, send: Send):
        limit = self._limit(scope)
        if limit is None:
            await self.app(scope, receive, send)
            return

        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        content_length = headers.get(b"content-length")
        if content_length is not None:
            try:
                declared = int(content_length)
            except ValueError:
                await self._reject(send, 400, "Invalid Content-Length")
                return
            if declared < 0:
                await self._reject(send, 400, "Invalid Content-Length")
                return
            if declared > limit:
                await self._reject(send, 413, "Request body is too large")
                return

        received = 0
        exceeded = False
        response_started = False

        async def limited_receive() -> ASGIMessage:
            nonlocal received, exceeded
            if exceeded:
                return {"type": "http.disconnect"}
            message = await receive()
            if message.get("type") == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    exceeded = True
                    return {"type": "http.disconnect"}
            return message

        async def tracked_send(message: ASGIMessage):
            nonlocal response_started
            if exceeded:
                return
            if message.get("type") == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracked_send)
        except RequestBodyTooLarge:
            exceeded = True
        if exceeded:
            if response_started:
                raise RequestBodyTooLarge
            await self._reject(send, 413, "Request body is too large")

    @staticmethod
    async def _reject(send: Send, status: int, detail: str):
        body = json.dumps({"detail": detail}, separators=(",", ":")).encode()
        await send({
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
                (b"connection", b"close"),
            ],
        })
        await send({"type": "http.response.body", "body": body})
