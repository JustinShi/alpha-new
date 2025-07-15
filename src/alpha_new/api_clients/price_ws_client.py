"""
价格推送WebSocket客户端
继承自BaseWebSocketClient，专门处理价格推送
"""

import asyncio
import json
from typing import Any

from src.alpha_new.api_clients.base_ws_client import BaseWebSocketClient
from src.alpha_new.models.ws_w3w_model import PRICE_WS_URL, PricePushModel


class PriceWebSocketClient(BaseWebSocketClient):
    """价格推送WebSocket客户端"""

    def __init__(self, headers: dict[str, str] | None = None, **kwargs) -> None:
        super().__init__(
            ws_url=PRICE_WS_URL, headers=headers, logger_name="price_ws", **kwargs
        )
        self._subscriptions: list[str] = []
        self._message_dedup = {}  # 消息去重缓存
        self._dedup_window = 100  # 保留最近100条消息ID

    async def _create_subscription_message(self, params: Any) -> dict:
        """创建价格订阅消息"""
        if isinstance(params, str):
            params = [params]
        elif not isinstance(params, list):
            params = [str(params)]

        # 保存订阅列表
        self._subscriptions.extend(params)

        return {"method": "SUBSCRIBE", "params": params, "id": len(self._subscriptions)}

    async def _process_message(self, message: dict) -> dict | None:
        """处理价格推送消息"""
        # 跳过订阅确认消息
        if "id" in message and ("result" in message or len(message) == 1):
            self.logger.debug(f"订阅确认: {message}")
            return None

        # 处理价格数据
        if "stream" in message and "data" in message:
            try:
                # 消息去重
                msg_key = (
                    f"{message['stream']}_{message['data'].get('k', {}).get('ot', '')}"
                )
                if msg_key in self._message_dedup:
                    self.logger.debug(f"重复消息已跳过: {msg_key}")
                    return None

                # 添加到去重缓存
                self._message_dedup[msg_key] = True
                if len(self._message_dedup) > self._dedup_window:
                    # 清理旧的缓存
                    oldest_keys = list(self._message_dedup.keys())[:10]
                    for key in oldest_keys:
                        del self._message_dedup[key]

                # 返回原始消息，让回调函数处理解析
                return message

            except Exception as e:
                self.logger.error(f"处理价格数据失败: {e}, 原始数据: {message}")
                return None

        return None

    async def subscribe_kline(self, symbol: str, interval: str = "1s") -> bool:
        """订阅K线数据

        Args:
            symbol: 交易对，格式如 "came@0xff7d6a96ae471bbcd7713af9cb1feeb16cf56b41@56"
            interval: K线周期，默认1s
        """
        stream_param = f"{symbol}@kline_{interval}"
        return await self.subscribe(stream_param)

    async def subscribe_multiple(self, streams: list[str]) -> bool:
        """批量订阅多个数据流"""
        return await self.subscribe(streams)

    async def unsubscribe(self, streams: list[str]) -> bool:
        """取消订阅"""
        if not self._ws or self._ws.closed:
            return False

        try:
            unsub_msg = {
                "method": "UNSUBSCRIBE",
                "params": streams,
                "id": len(self._subscriptions) + 1000,
            }
            await self._ws.send_str(json.dumps(unsub_msg))

            # 从订阅列表中移除
            for stream in streams:
                if stream in self._subscriptions:
                    self._subscriptions.remove(stream)

            self.logger.info(f"已取消订阅: {streams}")
            return True

        except Exception as e:
            self.logger.error(f"取消订阅失败: {e}")
            return False

    def get_subscriptions(self) -> list[str]:
        """获取当前订阅列表"""
        return self._subscriptions.copy()


# 使用示例
async def price_monitor_example() -> None:
    """价格监控示例"""

    # 消息处理回调
    async def on_price_message(data: dict) -> None:
        # 解析为Pydantic模型
        price_model = PricePushModel(**data)
        k = price_model.data.k
        print(
            f"[价格] {price_model.stream}: "
            f"开={k.o}, 高={k.h}, "
            f"低={k.l}, 收={k.c}, "
            f"量={k.v}"
        )

    # 创建客户端
    client = PriceWebSocketClient(
        headers={"User-Agent": "Mozilla/5.0"},
        heartbeat_interval=30,
        message_queue_size=1000,
    )

    # 设置回调
    client.set_callbacks(
        on_message=on_price_message,
        on_connect=lambda: print("价格WebSocket已连接"),
        on_disconnect=lambda: print("价格WebSocket已断开"),
    )

    # 连接并订阅
    if await client.connect():
        # 订阅单个
        await client.subscribe_kline(
            "came@0xff7d6a96ae471bbcd7713af9cb1feeb16cf56b41@56"
        )

        # 或批量订阅
        # await client.subscribe_multiple([
        #     "came@0xff7d6a96ae471bbcd7713af9cb1feeb16cf56b41@56@kline_1s",
        #     "btc@0x1234567890abcdef@1@kline_1m"
        # ])

        # 运行30秒
        await asyncio.sleep(30)

        # 获取统计信息
        stats = client.get_stats()
        print(f"统计信息: {stats}")

        # 断开连接
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(price_monitor_example())
