import json
import logging
import time
import uuid
from contextvars import ContextVar

from starlette.types import ASGIApp, Message, Receive, Scope, Send

request_id_context: ContextVar[str] = ContextVar("request_id", default="-")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            {
                "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%SZ"),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "request_id": request_id_context.get(),
            },
            separators=(",", ":"),
        )


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.logger = logging.getLogger("munnin.request")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope["headers"])
        request_id = headers.get(b"x-request-id", b"").decode()[:128] or str(uuid.uuid4())
        token = request_id_context.set(request_id)
        started = time.monotonic()
        status_code = 500

        async def send_with_headers(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                message.setdefault("headers", []).append((b"x-request-id", request_id.encode()))
            await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
        finally:
            self.logger.info(
                "request completed method=%s path=%s status=%d duration_ms=%d",
                scope["method"],
                scope["path"],
                status_code,
                int((time.monotonic() - started) * 1000),
            )
            request_id_context.reset(token)


class BodyLimitMiddleware:
    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        content_length = dict(scope["headers"]).get(b"content-length")
        if content_length and int(content_length) > self.max_bytes:
            await self._reject(send)
            return
        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise RequestTooLargeError
            return message

        try:
            await self.app(scope, limited_receive, send)
        except RequestTooLargeError:
            await self._reject(send)

    @staticmethod
    async def _reject(send: Send) -> None:
        body = b'{"detail":"Request body too large"}'
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [(b"content-type", b"application/json"), (b"content-length", b"35")],
            }
        )
        await send({"type": "http.response.body", "body": body})


class RequestTooLargeError(Exception):
    pass
