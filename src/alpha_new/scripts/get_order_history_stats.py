import asyncio
from datetime import datetime, timedelta
import json

from rich.console import Console
from rich.table import Table
import toml

from alpha_new.api.alpha_api import AlphaAPI
from alpha_new.db.models import init_db
from alpha_new.db.ops import get_user_by_id, get_valid_users
from alpha_new.utils import get_script_logger


# 辅助函数: 将dict的key/value从bytes转str
def decode_dict(d) -> dict[str, str]:
    if not d:
        return {}
    return {
        k.decode() if isinstance(k, bytes) else k: v.decode()
        if isinstance(v, bytes)
        else v
        for k, v in d.items()
    }


console = Console()
logger = get_script_logger()

CONFIG_PATH = "config/airdrop_config.toml"


def get_time_range():
    now = datetime.now()
    today_8 = now.replace(hour=8, minute=0, second=0, microsecond=0)
    if now < today_8:
        start = today_8 - timedelta(days=1)
        end = today_8
    else:
        start = today_8
        end = today_8 + timedelta(days=1)
    # 转为毫秒时间戳
    return int(start.timestamp() * 1000), int(end.timestamp() * 1000)


def load_symbol_map_from_file(path="data/token_info.json"):
    try:
        with open(path, encoding="utf-8") as f:
            tokens = json.load(f)
        return {
            item["alphaId"]: item["symbol"]
            for item in tokens
            if "alphaId" in item and "symbol" in item
        }
    except Exception as e:
        logger.warning(f"加载本地币种映射失败: {e}")
        return {}


async def fetch_token_symbol_map(api: AlphaAPI) -> dict[str, str]:
    # 通过AlphaAPI方法获取币种symbol与baseAsset映射
    data = await api.get_token_list()
    symbol_map = {}
    if data.get("code") == "000000":
        for item in data["data"]:
            if "baseAsset" in item and "symbol" in item:
                symbol_map[item["baseAsset"]] = item["symbol"]
    return symbol_map


async def get_user_order_stats(
    user_id: int, engine, symbol_map: dict[str, str], start_ms: int, end_ms: int
) -> dict:
    from sqlalchemy.ext.asyncio import async_sessionmaker

    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        user = await get_user_by_id(session, user_id)
        if not user:
            return {"user_id": user_id, "orders": []}
        headers = decode_dict(user.headers) if user.headers is not None else {}
        cookies = decode_dict(user.cookies) if user.cookies is not None else None
        api = AlphaAPI(headers=headers, cookies=cookies)
        # 拉取所有订单（自动分页）
        page = 1
        rows = 500
        all_orders = []
        total = None
        while True:
            params = {
                "page": page,
                "rows": rows,
                "orderStatus": "FILLED",
                "startTime": start_ms,
                "endTime": end_ms,
            }
            try:
                resp = await api.get_order_history(params)
                orders = resp.get("data", [])
                if total is None:
                    total = resp.get("total", 0)
                all_orders.extend(orders)
                if len(all_orders) >= total or not orders:
                    break
                page += 1
            except Exception as e:
                logger.error(f"用户{user_id}订单查询失败: {e}")
                break
        # 统计
        stats = {}
        for order in all_orders:
            # 优先用baseAsset映射symbol，其次alphaId，最后fallback
            alpha_id = order.get("alphaId")
            token = order.get("baseAsset")
            # 优先用baseAsset（如MPLX）做映射
            symbol = symbol_map.get(token)
            if not symbol:
                symbol = symbol_map.get(alpha_id)
            if not symbol:
                symbol = token or alpha_id or "-"
            side = order.get("side")
            quote_asset = order.get("quoteAsset")
            if quote_asset != "USDT":
                continue  # 只统计USDT计价
            qty = float(order.get("executedQty", 0))
            avg_price = float(order.get("avgPrice", 0))
            amount = qty * avg_price
            if symbol not in stats:
                stats[symbol] = {"buy": 0, "sell": 0}
            if side == "BUY":
                stats[symbol]["buy"] += amount
            elif side == "SELL":
                stats[symbol]["sell"] += amount
        # 计算净额
        for symbol in stats:
            stats[symbol]["net"] = stats[symbol]["buy"] - stats[symbol]["sell"]
        return {"user_id": user_id, "stats": stats}


async def main():
    config = toml.load(CONFIG_PATH)
    engine = await init_db("sqlite+aiosqlite:///data/alpha_users.db")
    from sqlalchemy.ext.asyncio import async_sessionmaker

    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        users = await get_valid_users(session)
        user_ids = [user.id for user in users]
    logger.info(f"检测到数据库用户: {user_ids}")
    # 获取symbol映射，优先本地文件
    symbol_map = load_symbol_map_from_file()
    if not symbol_map and user_ids:
        user = await get_user_by_id(async_session(), user_ids[0])
        headers = decode_dict(user.headers) if user and user.headers is not None else {}
        cookies = (
            decode_dict(user.cookies) if user and user.cookies is not None else None
        )
        api = AlphaAPI(headers=headers, cookies=cookies, user_id=user_ids[0])
        symbol_map = await fetch_token_symbol_map(api)
    # 自动时间区间
    start_ms, end_ms = get_time_range()
    logger.info(
        f"查询时间区间: {datetime.fromtimestamp(start_ms/1000)} ~ {datetime.fromtimestamp(end_ms/1000)}"
    )
    # 查询所有用户订单
    tasks = [
        get_user_order_stats(uid, engine, symbol_map, start_ms, end_ms)
        for uid in user_ids
    ]
    results = await asyncio.gather(*tasks)
    # 输出表格
    table = Table(title="用户订单历史统计（按代币）")
    table.add_column("用户ID", justify="right")
    table.add_column("代币", justify="left")
    table.add_column("买入总额", justify="right")
    table.add_column("卖出总额", justify="right")
    table.add_column("净额", justify="right")
    for idx, res in enumerate(results):
        user_id = str(res["user_id"])
        stats = res["stats"]
        first = True
        for symbol, s in stats.items():
            table.add_row(
                user_id if first else "",
                symbol,
                f"{s['buy']:.4f}",
                f"{s['sell']:.4f}",
                f"{s['net']:.4f}",
            )
            first = False
        # 如果不是最后一个用户，插入分割行
        if idx < len(results) - 1:
            table.add_row("─" * 6, "─" * 6, "─" * 10, "─" * 10, "─" * 10)
    console.print(table)


if __name__ == "__main__":
    asyncio.run(main())
