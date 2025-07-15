"""
WebSocket客户端基类
提供通用的连接管理、消息处理、重连机制等功能
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

import aiohttp


class BaseWebSocketClient(ABC):
    """WebSocket客户端基类"""

    def __init__(
        self,
        ws_url: str,
        headers: dict[str, str] | None = None,
        session: aiohttp.ClientSession | None = None,
        logger_name: str = "ws_client",
        reconnect_attempts: int = 5,
        reconnect_delay: int = 3,
        heartbeat_interval: int = 30,
        message_queue_size: int = 1000,
    ) -> None:
        self.ws_url = ws_url
        self.headers = headers or {}
        self.session = session
        self.reconnect_attempts = reconnect_attempts
        self.reconnect_delay = reconnect_delay
        self.heartbeat_interval = heartbeat_interval
        self.message_queue_size = message_queue_size

        # 日志配置
        self.logger = logging.getLogger(logger_name)

        # 连接状态
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._running = False
        self._heartbeat_task: asyncio.Task | None = None
        self._last_heartbeat = datetime.now()

        # 消息队列
        self._message_queue: asyncio.Queue = asyncio.Queue(maxsize=message_queue_size)

        # 统计信息
        self.stats = {
            "messages_received": 0,
            "messages_processed": 0,
            "errors": 0,
            "reconnects": 0,
            "last_message_time": None,
            "connection_start_time": None,
        }

        # 回调函数
        self._on_message: Callable | None = None
        self._on_error: Callable | None = None
        self._on_connect: Callable | None = None
        self._on_disconnect: Callable | None = None

    @abstractmethod
    async def _create_subscription_message(self, params: Any) -> dict:
        """创建订阅消息（子类实现）"""

    @abstractmethod
    async def _process_message(self, message: dict) -> Any | None:
        """处理接收到的消息（子类实现）"""

    async def connect(self) -> bool:
        """建立WebSocket连接"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            self._ws = await self.session.ws_connect(
                self.ws_url, headers=self.headers, heartbeat=self.heartbeat_interval
            )

            self._running = True
            self.stats["connection_start_time"] = datetime.now()

            # 启动心跳
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

            # 触发连接回调
            if self._on_connect:
                await self._call_callback(self._on_connect)

            self.logger.info(f"WebSocket连接成功: {self.ws_url}")
            return True

        except Exception as e:
            self.logger.error(f"WebSocket连接失败: {e}")
            self.stats["errors"] += 1
            return False

    async def disconnect(self) -> None:
        """断开WebSocket连接"""
        self._running = False

        if self._heartbeat_task:
            self._heartbeat_task.cancel()

        if self._ws and not self._ws.closed:
            await self._ws.close()

        # 触发断开回调
        if self._on_disconnect:
            await self._call_callback(self._on_disconnect)

        self.logger.info("WebSocket连接已断开")

    async def subscribe(self, params: Any) -> bool:
        """发送订阅请求"""
        if not self._ws or self._ws.closed:
            self.logger.error("WebSocket未连接，无法订阅")
            return False

        try:
            sub_msg = await self._create_subscription_message(params)
            await self._ws.send_str(json.dumps(sub_msg))
            self.logger.info(f"已发送订阅: {sub_msg}")
            return True
        except Exception as e:
            self.logger.error(f"订阅失败: {e}")
            return False

    async def _reconnect_with_backoff(self) -> bool:
        """重连机制（使用指数退避）"""
        for attempt in range(self.reconnect_attempts):
            self.stats["reconnects"] += 1
            self.logger.info(f"尝试重连... (第{self.stats['reconnects']}次)")

            await self.disconnect()

            # 指数退避延迟
            delay = self.reconnect_delay * (2**attempt)
            delay = min(delay, 60)  # 最大延迟60秒
            await asyncio.sleep(delay)

            if await self.connect():
                self.logger.info("重连成功")
                return True

        self.logger.error(f"重连失败，已尝试{self.reconnect_attempts}次")
        return False

    async def _heartbeat_loop(self) -> None:
        """心跳循环"""
        while self._running:
            try:
                if self._ws and not self._ws.closed:
                    # 发送ping
                    await self._ws.ping()
                    self._last_heartbeat = datetime.now()

                    # 检查是否长时间没有收到消息
                    if self.stats["last_message_time"]:
                        time_since_last_msg = (
                            datetime.now() - self.stats["last_message_time"]
                        )
                        if time_since_last_msg > timedelta(minutes=5):
                            self.logger.warning("超过5分钟未收到消息，尝试重连")
                            await self._reconnect_with_backoff()

                await asyncio.sleep(self.heartbeat_interval)

            except Exception as e:
                self.logger.error(f"心跳异常: {e}")
                await self._reconnect_with_backoff()

    async def _message_loop(self) -> None:
        """消息接收循环"""
        while self._running:
            try:
                if not self._ws or self._ws.closed:
                    await self._reconnect_with_backoff()
                    continue

                async for msg in self._ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        self.stats["messages_received"] += 1
                        self.stats["last_message_time"] = datetime.now()

                        try:
                            data = json.loads(msg.data)

                            # 处理消息
                            processed = await self._process_message(data)
                            if processed is not None:
                                # 加入队列
                                if not self._message_queue.full():
                                    await self._message_queue.put(processed)

                                # 触发回调
                                if self._on_message:
                                    await self._call_callback(
                                        self._on_message, processed
                                    )

                                self.stats["messages_processed"] += 1

                        except json.JSONDecodeError as e:
                            self.logger.error(f"JSON解析错误: {e}")

                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        self.logger.error(f"WebSocket错误: {msg}")
                        self.stats["errors"] += 1
                        if self._on_error:
                            await self._call_callback(self._on_error, msg)
                        break

                    elif msg.type == aiohttp.WSMsgType.CLOSED:
                        self.logger.warning("WebSocket连接已关闭")
                        break

            except Exception as e:
                self.logger.error(f"消息循环异常: {e}")
                self.stats["errors"] += 1
                await asyncio.sleep(self.reconnect_delay)

    async def _call_callback(self, callback: Callable, *args, **kwargs) -> None:
        """安全调用回调函数"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(*args, **kwargs)
            else:
                callback(*args, **kwargs)
        except Exception as e:
            self.logger.error(f"回调函数执行异常: {e}")

    async def run(self) -> None:
        """启动客户端"""
        if await self.connect():
            await self._message_loop()

    def set_callbacks(
        self,
        on_message: Callable | None = None,
        on_error: Callable | None = None,
        on_connect: Callable | None = None,
        on_disconnect: Callable | None = None,
    ) -> None:
        """设置回调函数"""
        if on_message:
            self._on_message = on_message
        if on_error:
            self._on_error = on_error
        if on_connect:
            self._on_connect = on_connect
        if on_disconnect:
            self._on_disconnect = on_disconnect

    async def get_messages(self, timeout: float | None = None) -> list[Any]:
        """从队列获取消息"""
        messages = []
        try:
            while not self._message_queue.empty():
                msg = await asyncio.wait_for(self._message_queue.get(), timeout=timeout)
                messages.append(msg)
        except TimeoutError:
            pass
        return messages

    def get_stats(self) -> dict:
        """获取统计信息"""
        stats = self.stats.copy()
        if stats["connection_start_time"]:
            stats["uptime"] = str(datetime.now() - stats["connection_start_time"])
        stats["queue_size"] = self._message_queue.qsize()
        return stats
