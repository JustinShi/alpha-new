"""
统一异步HTTP客户端,支持代理池配置
"""

import asyncio

import httpx


class HTTPClientFactory:
    _client: httpx.AsyncClient | None = None
    _proxies: dict[str, str] | None = None

    @classmethod
    def set_proxies(cls, proxies: dict[str, str] | None = None) -> None:
        cls._proxies = proxies
        if cls._client:
            # 关闭旧client,重建新client
            _close_task = asyncio.create_task(cls._client.aclose())  # noqa: RUF006
            cls._client = None

    @classmethod
    def get_client(cls) -> httpx.AsyncClient:
        if cls._client is None:
            if cls._proxies:
                # 假设代理格式为 {"http": "proxy_url", "https": "proxy_url"}
                proxy_url = cls._proxies.get("http") or cls._proxies.get("https")
                cls._client = httpx.AsyncClient(proxy=proxy_url)
            else:
                cls._client = httpx.AsyncClient()
        return cls._client
