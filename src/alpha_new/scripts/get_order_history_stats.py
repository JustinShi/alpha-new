import asyncio
from datetime import datetime
import json
import logging

from rich.console import Console
from rich.table import Table
import toml

from alpha_new.api.alpha_api import AlphaAPI
from alpha_new.db.models import init_db
from alpha_new.db.ops import get_all_user_ids, get_user_by_id, get_valid_users
from alpha_new.utils import get_script_logger

# 设置API日志级别，减少终端输出
logging.getLogger('alpha_new.api').setLevel(logging.WARNING)


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


def get_today_8am_range_ms():
    """
    以8点为分界线定义"今天"：
    - 如果当前时间 < 今天8点：查询昨天8点到今天8点
    - 如果当前时间 ≥ 今天8点：查询今天8点到明天8点

    返回: (start_ms, end_ms) 毫秒时间戳
    """
    from datetime import datetime, timedelta

    now = datetime.now()
    today_8am = now.replace(hour=8, minute=0, second=0, microsecond=0)

    if now < today_8am:
        # 当前时间小于今天8点，查询昨天8点到今天8点
        start_time = today_8am - timedelta(days=1)
        end_time = today_8am
    else:
        # 当前时间大于等于今天8点，查询今天8点到明天8点
        start_time = today_8am
        end_time = today_8am + timedelta(days=1)

    return int(start_time.timestamp() * 1000), int(end_time.timestamp() * 1000)


def get_recent_days_range_ms(days: int = 7):
    """
    获取最近N天的时间范围（毫秒时间戳）

    Args:
        days: 天数，默认7天

    Returns:
        (start_ms, end_ms) 毫秒时间戳
    """
    from datetime import datetime, timedelta

    now = datetime.now()
    start_time = now - timedelta(days=days)

    return int(start_time.timestamp() * 1000), int(now.timestamp() * 1000)


# 使用新的时间工具模块，保持向后兼容
def get_time_range():
    """
    以8点为分界线定义"今天"：
    - 如果当前时间 < 今天8点：查询昨天8点到今天8点
    - 如果当前时间 ≥ 今天8点：查询今天8点到明天8点

    注意：此函数已迁移到 time_utils 模块，这里保持向后兼容
    """
    return get_today_8am_range_ms()


def load_symbol_map_from_file(path="data/token_info.json"):
    try:
        with open(path, encoding="utf-8") as f:
            token_data = json.load(f)

        # 处理新的JSON结构
        tokens = token_data.get("tokens", []) if isinstance(token_data, dict) else token_data

        symbol_map = {}
        for item in tokens:
            # 优先使用alphaId映射
            if "alphaId" in item and "symbol" in item and item["alphaId"]:
                symbol_map[item["alphaId"]] = item["symbol"]
            # 其次使用baseAsset映射
            if "baseAsset" in item and "symbol" in item and item["baseAsset"]:
                symbol_map[item["baseAsset"]] = item["symbol"]

        # 添加已知的手动映射
        manual_mappings = {
            "ALPHA_259": "CROSS",
            "ALPHA_285": "MPLX",
            # 可以根据需要添加更多映射
        }
        symbol_map.update(manual_mappings)

        return symbol_map
    except Exception as e:
        logger.warning(f"加载本地币种映射失败: {e}")
        # 返回基本的手动映射作为后备
        return {
            "ALPHA_259": "CROSS",
            "ALPHA_285": "MPLX",
        }


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

    # 诊断用户状态
    async with async_session() as session:
        all_users = await get_all_user_ids(session)
        valid_users = await get_valid_users(session)
        user_ids = [user.id for user in valid_users]

    logger.info(f"总用户数: {len(all_users)}, 有效用户数: {len(user_ids)}")
    logger.info(f"有效用户ID: {user_ids}")

    if not user_ids:
        console.print("❌ 没有找到有效用户，请检查用户登录状态", style="red")
        # 显示所有用户的状态
        async with async_session() as session:
            for user_id in all_users:
                user = await get_user_by_id(session, user_id)
                if user:
                    console.print(
                        f"用户{user_id}: {user.name} - 状态: {user.login_status}"
                    )
        return

    # 获取symbol映射，优先本地文件
    symbol_map = load_symbol_map_from_file()
    if not symbol_map and user_ids:
        async with async_session() as session:
            user = await get_user_by_id(session, user_ids[0])
            headers = (
                decode_dict(user.headers) if user and user.headers is not None else {}
            )
            cookies = (
                decode_dict(user.cookies) if user and user.cookies is not None else None
            )
            api = AlphaAPI(headers=headers, cookies=cookies, user_id=user_ids[0])
            symbol_map = await fetch_token_symbol_map(api)

    # 简化时间范围选择，直接使用今天8点分界
    console.print("\n📅 使用时间范围: 今天(8点分界)")

    # 默认使用今天(8点分界)
    start_ms, end_ms = get_today_8am_range_ms()
    logger.info(
        f"查询时间区间: {datetime.fromtimestamp(start_ms/1000)} ~ {datetime.fromtimestamp(end_ms/1000)}"
    )

    # 查询所有用户订单
    console.print(f"🔍 正在查询 {len(user_ids)} 个用户的订单历史...")
    tasks = [
        get_user_order_stats(uid, engine, symbol_map, start_ms, end_ms)
        for uid in user_ids
    ]
    results = await asyncio.gather(*tasks)

    # 检查结果
    total_orders = sum(len(res.get("stats", {})) for res in results)
    logger.info(f"总共找到 {total_orders} 个代币的交易记录")

    # 输出表格
    table = Table(title="用户订单历史统计（按代币）")
    table.add_column("用户ID", justify="right")
    table.add_column("代币", justify="left")
    table.add_column("买入总额", justify="right")
    table.add_column("卖出总额", justify="right")
    table.add_column("净额", justify="right")

    has_data = False
    for idx, res in enumerate(results):
        user_id = str(res["user_id"])
        stats = res.get("stats", {})

        if not stats:
            table.add_row(user_id, "无交易记录", "0.00", "0.00", "0.00")
            continue

        has_data = True
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

    if not has_data:
        console.print("\n💡 提示: 如果没有找到交易记录，可能的原因:", style="yellow")
        console.print("   1. 选择的时间范围内没有交易")
        console.print("   2. 用户认证信息过期")
        console.print("   3. API权限不足")
        console.print(
            "   建议运行增强版诊断工具: python -m alpha_new.scripts.enhanced_order_stats"
        )


def get_extended_time_range(days: int):
    """
    获取扩展时间范围

    注意：此函数已迁移到 time_utils 模块，这里保持向后兼容
    """
    return get_recent_days_range_ms(days)


if __name__ == "__main__":
    asyncio.run(main())
