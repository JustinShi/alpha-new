import asyncio
import contextlib
from typing import Any

import httpx

from ..utils import get_api_logger
from ..utils.http_pool import BINANCE_CLIENT_CONFIG, get_http_client

BASE_URL = "https://www.binance.com"
logger = get_api_logger()


class AlphaAPI:
    def __init__(
        self,
        headers: dict[str, str],
        cookies: dict[str, str] | None = None,
        user_id: int | None = None,
    ):
        self.headers = headers
        self.cookies = cookies
        self.user_id = user_id  # 添加用户ID用于日志追踪
        self._client = None
        self._client_lock = asyncio.Lock()

    async def _get_client(self) -> httpx.AsyncClient:
        """获取HTTP客户端（优化版本 - 使用全局连接池）"""
        # 🚀 优化：使用全局连接池，为每个用户创建独立的客户端ID
        client_id = (
            f"binance_user_{self.user_id}" if self.user_id else "binance_default"
        )
        return await get_http_client(
            client_id=client_id,
            base_url=str(BINANCE_CLIENT_CONFIG["base_url"]),
            timeout=float(BINANCE_CLIENT_CONFIG["timeout"]),
        )

    async def close(self):
        """关闭HTTP客户端连接池（已优化为全局连接池，无需手动关闭）"""
        # 🚀 优化：使用全局连接池，无需手动关闭
        # 连接池会自动管理连接的生命周期

    async def get_user_info(self) -> Any:
        url = f"{BASE_URL}/bapi/accounts/v1/private/account/user/base-detail"
        user_prefix = f"[用户{self.user_id}] " if self.user_id else ""
        logger.info(f"{user_prefix}POST {url}")
        client = await self._get_client()
        resp = await client.post(
            url, headers=self.headers, cookies=self.cookies, json={}
        )
        logger.info(f"{user_prefix}Response {resp.status_code}: {resp.text[:200]}")
        resp.raise_for_status()
        return resp.json()

    async def get_alpha_score(self) -> Any:
        url = f"{BASE_URL}/bapi/defi/v1/private/wallet-direct/buw/tge/common/user-score"
        user_prefix = f"[用户{self.user_id}] " if self.user_id else ""
        logger.info(f"{user_prefix}GET {url}")
        client = await self._get_client()
        resp = await client.get(url, headers=self.headers, cookies=self.cookies)
        logger.info(f"{user_prefix}Response {resp.status_code}: {resp.text[:200]}")
        resp.raise_for_status()
        return resp.json()

    async def get_wallet_balance(self) -> Any:
        """查询所有币种余额"""
        url = f"{BASE_URL}/bapi/asset/v2/private/asset-service/wallet/asset?needAlphaAsset=1&quoteAsset=USDT"
        user_prefix = f"[用户{self.user_id}] " if self.user_id else ""
        logger.info(f"{user_prefix}GET {url}")
        client = await self._get_client()
        resp = await client.get(url, headers=self.headers, cookies=self.cookies)
        logger.info(f"{user_prefix}Response {resp.status_code}: {resp.text[:200]}")
        resp.raise_for_status()
        return resp.json()

    async def query_airdrop_list(self, page: int = 1, rows: int = 50) -> Any:
        url = f"{BASE_URL}/bapi/defi/v1/friendly/wallet-direct/buw/growth/query-alpha-airdrop"
        payload = {"page": page, "rows": rows}
        user_prefix = f"[用户{self.user_id}] " if self.user_id else ""
        logger.info(f"{user_prefix}POST {url} | payload={payload}")

        try:
            client = await self._get_client()
            resp = await client.post(
                url, headers=self.headers, cookies=self.cookies, json=payload
            )
            logger.info(f"{user_prefix}Response {resp.status_code}: {resp.text[:200]}")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"{user_prefix}查询空投列表请求失败: {e}")
            # 如果是连接问题，清理客户端以便下次重新创建
            if (
                "NoneType" in str(e)
                or "send" in str(e)
                or "connection" in str(e).lower()
            ):
                logger.warning(f"{user_prefix}检测到连接问题，清理HTTP客户端")
                if hasattr(self, "_client") and self._client:
                    with contextlib.suppress(Exception):
                        await self._client.aclose()
                    self._client = None
            raise

    async def claim_airdrop(self, config_id: str) -> Any:
        url = f"{BASE_URL}/bapi/defi/v1/private/wallet-direct/buw/growth/claim-alpha-airdrop"
        user_prefix = f"[用户{self.user_id}] " if self.user_id else ""
        logger.info(f"{user_prefix}POST {url} | config_id={config_id}")
        try:
            client = await self._get_client()
            resp = await client.post(
                url,
                headers=self.headers,
                cookies=self.cookies,
                json={"configId": config_id},
            )
            logger.info(f"{user_prefix}Response {resp.status_code}: {resp.text}")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"{user_prefix}claim_airdrop接口异常: {e}")
            raise

    async def get_market_quote(
        self,
        from_asset: str,
        to_asset: str,
        from_amount: str | float,
        slippage: str | float,
    ) -> Any:
        url = f"{BASE_URL}/bapi/defi/v1/private/wallet-direct/swap/cex/get-quote"
        payload = {
            "fromAsset": from_asset,
            "toAsset": to_asset,
            "fromAmount": str(from_amount),
            "slippage": str(slippage),
        }
        logger.info(f"POST {url} | payload={payload}")
        client = await self._get_client()
        resp = await client.post(
            url, headers=self.headers, cookies=self.cookies, json=payload
        )
        logger.info(f"Response {resp.status_code}: {resp.text[:200]}")
        resp.raise_for_status()
        return resp.json()

    async def market_buy(
        self,
        quote_id: str,
        from_asset: str,
        to_asset: str,
        from_amount: str | float,
        slippage: str | float,
    ) -> Any:
        url = f"{BASE_URL}/bapi/defi/v2/private/wallet-direct/swap/cex/buy/pre/payment"
        payload = {
            "quoteId": quote_id,
            "fromAsset": from_asset,
            "toAsset": to_asset,
            "fromAmount": str(from_amount),
            "slippage": str(slippage),
        }
        logger.info(f"POST {url} | payload={payload}")
        client = await self._get_client()
        resp = await client.post(
            url, headers=self.headers, cookies=self.cookies, json=payload
        )
        logger.info(f"Response {resp.status_code}: {resp.text[:200]}")
        resp.raise_for_status()
        return resp.json()

    async def market_sell(
        self,
        quote_id: str,
        from_asset: str,
        to_asset: str,
        from_amount: str | float,
        slippage: str | float,
    ) -> Any:
        url = f"{BASE_URL}/bapi/defi/v2/private/wallet-direct/swap/cex/sell/pre/payment"
        payload = {
            "quoteId": quote_id,
            "fromAsset": from_asset,
            "toAsset": to_asset,
            "fromAmount": str(from_amount),
            "slippage": str(slippage),
        }
        logger.info(f"POST {url} | payload={payload}")
        client = await self._get_client()
        resp = await client.post(
            url, headers=self.headers, cookies=self.cookies, json=payload
        )
        logger.info(f"Response {resp.status_code}: {resp.text[:200]}")
        resp.raise_for_status()
        return resp.json()

    async def place_limit_order(
        self,
        base_asset: str,
        quote_asset: str,
        side: str,
        price: str | float,
        quantity: str | float,
        payment_details: list[dict] | None = None,
        time_in_force: str = "GTC",
    ) -> Any:
        url = f"{BASE_URL}/bapi/asset/v1/private/alpha-trade/order/place"
        payload: dict[str, Any] = {
            "baseAsset": base_asset,
            "quoteAsset": quote_asset,
            "side": side,
            "price": price,
            "quantity": quantity,
        }
        if payment_details is not None:
            payload["paymentDetails"] = payment_details
        # type和timeInForce如API不需要可省略
        logger.info(f"POST {url} | payload={payload}")
        client = await self._get_client()
        resp = await client.post(
            url, headers=self.headers, cookies=self.cookies, json=payload
        )
        logger.info(f"Response {resp.status_code}: {resp.text[:200]}")
        resp.raise_for_status()
        return resp.json()

    async def cancel_order(
        self, order_id: str, base_asset: str, quote_asset: str
    ) -> Any:
        url = f"{BASE_URL}/bapi/asset/v1/private/alpha-trade/order/cancel"
        payload = {
            "orderId": order_id,
            "baseAsset": base_asset,
            "quoteAsset": quote_asset,
        }
        logger.info(f"POST {url} | payload={payload}")
        client = await self._get_client()
        resp = await client.post(
            url, headers=self.headers, cookies=self.cookies, json=payload
        )
        logger.info(f"Response {resp.status_code}: {resp.text[:200]}")
        resp.raise_for_status()
        return resp.json()

    async def get_order_history(self, params: dict[str, Any] | None = None) -> Any:
        url = (
            f"{BASE_URL}/bapi/defi/v1/private/alpha-trade/order/get-order-history-merge"
        )
        logger.info(f"GET {url} | params={params}")
        client = await self._get_client()
        resp = await client.get(
            url, headers=self.headers, cookies=self.cookies, params=params
        )
        logger.info(f"Response {resp.status_code}: {resp.text[:200]}")
        resp.raise_for_status()
        return resp.json()

    async def get_listen_key(self) -> Any:
        url = f"{BASE_URL}/bapi/defi/v1/private/alpha-trade/get-listen-key"
        logger.info(f"POST {url}")
        client = await self._get_client()
        resp = await client.post(
            url, headers=self.headers, cookies=self.cookies, json={}
        )
        logger.info(f"Response {resp.status_code}: {resp.text[:200]}")
        resp.raise_for_status()
        return resp.json()

    async def get_token_list(self) -> Any:
        url = "https://www.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/cex/alpha/all/token/list"
        client = await self._get_client()
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()
