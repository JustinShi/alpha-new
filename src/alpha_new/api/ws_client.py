import asyncio
import contextlib
import json
from collections.abc import Awaitable, Callable
from typing import Any

import websockets

from .http_client import HTTPClientFactory
from .utils import APIError, async_retry


class AlphaWebSocketClient:
    def __init__(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        heartbeat_interval: float = 30.0,
    ):
        self.url = url
        self.headers = headers or {}
        self.heartbeat_interval = heartbeat_interval
        self._ws: Any = None
        self._running = False
        self._on_message: Callable[[dict[str, Any]], Awaitable[None]] | None = None
        self._on_error: Callable[[Exception], Awaitable[None]] | None = None
        self._heartbeat_task: asyncio.Task[None] | None = None
        self._listen_task: asyncio.Task[None] | None = None

    def on_message(self, callback: Callable[[dict[str, Any]], Awaitable[None]]) -> None:
        self._on_message = callback

    def on_error(self, callback: Callable[[Exception], Awaitable[None]]) -> None:
        self._on_error = callback

    @async_retry(max_retries=5, delay=3, exceptions=(Exception,))
    async def connect(self) -> None:
        proxies = HTTPClientFactory._proxies
        proxy = proxies["all"] if proxies and "all" in proxies else None
        self._ws = await websockets.connect(
            self.url, extra_headers=self.headers, proxy=proxy
        )
        self._running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat())
        self._listen_task = asyncio.create_task(self._listen())

    async def _listen(self) -> None:
        if not self._ws:
            return
        try:
            async for msg in self._ws:
                try:
                    data = json.loads(msg)
                    if self._on_message:
                        await self._on_message(data)
                except Exception as e:
                    if self._on_error:
                        await self._on_error(e)
        except Exception as e:
            self._running = False
            if self._on_error:
                await self._on_error(e)
            await self._reconnect()

    async def send(self, data: dict[str, Any]) -> None:
        if not self._ws:
            raise APIError("WebSocket未连接")
        await self._ws.send(json.dumps(data))

    async def close(self) -> None:
        self._running = False
        if self._ws:
            await self._ws.close()
        if self._heartbeat_task:
            self._heartbeat_task.cancel()

    async def _heartbeat(self) -> None:
        while self._running:
            with contextlib.suppress(Exception):
                await self.send({"method": "PING"})
            await asyncio.sleep(self.heartbeat_interval)

    async def _reconnect(self) -> None:
        await asyncio.sleep(3)
        try:
            await self.connect()
        except Exception as e:
            if self._on_error:
                await self._on_error(e)
