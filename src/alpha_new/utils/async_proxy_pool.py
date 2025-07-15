import asyncio
import logging
import random

import aiofiles

logger = logging.getLogger(__name__)


class AsyncProxyPool:
    def __init__(self, proxies: list[str]) -> None:
        self._proxies = proxies
        self._index = 0
        self._lock = asyncio.Lock()

    @classmethod
    async def from_file(cls, filepath: str) -> "AsyncProxyPool":
        proxies = []
        try:
            async with asyncio.Lock(), aiofiles.open(filepath, encoding="utf-8") as f:
                async for line in f:
                    stripped_line = line.strip()
                    if stripped_line and not stripped_line.startswith("#"):
                        proxies.append(stripped_line)
        except Exception as e:
            logger.error(f"加载代理文件失败: {e}")
        return cls(list(set(proxies)))

    async def get_random(self) -> str | None:
        async with self._lock:
            if not self._proxies:
                return None
            return random.choice(self._proxies)

    async def get_next(self) -> str | None:
        async with self._lock:
            if not self._proxies:
                return None
            proxy = self._proxies[self._index]
            self._index = (self._index + 1) % len(self._proxies)
            return proxy

    async def remove(self, proxy: str) -> None:
        async with self._lock:
            if proxy in self._proxies:
                self._proxies.remove(proxy)
                if self._index >= len(self._proxies):
                    self._index = 0

    async def add(self, proxy: str) -> None:
        async with self._lock:
            if proxy not in self._proxies:
                self._proxies.append(proxy)

    async def count(self) -> int:
        async with self._lock:
            return len(self._proxies)


if __name__ == "__main__":

    async def test() -> None:
        pool = await AsyncProxyPool.from_file("config/proxies.txt")
        logger.info(await pool.get_random())
        logger.info(await pool.get_next())
        await pool.remove("http://127.0.0.1:1080")
        logger.info(await pool.count())
        logger.info(await pool.get_next())

    asyncio.run(test())
