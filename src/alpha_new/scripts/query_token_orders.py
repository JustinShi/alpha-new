#!/usr/bin/env python3
"""
查询配置文件指定代币的历史订单脚本

使用类似 get_time_range() 的方法查询指定代币在特定时间范围内的历史订单
"""

import asyncio
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import async_sessionmaker
import toml

from alpha_new.api.alpha_api import AlphaAPI
from alpha_new.db.models import init_db
from alpha_new.db.ops import get_valid_users
from alpha_new.utils.logger import get_api_logger

logger = get_api_logger()


def get_time_range():
    """
    获取以每天上午8点为分界点的时间范围

    Returns:
        tuple: (start_time_ms, end_time_ms) 毫秒时间戳
    """
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


async def fetch_all_orders(
    api: AlphaAPI, base_asset: str, side: str, start_time: int, end_time: int
) -> list:
    """
    获取所有订单数据，支持多页合并

    Args:
        api: API客户端
        base_asset: 基础资产，如 "ALPHA_259"
        side: 订单方向，"BUY" 或 "SELL"
        start_time: 开始时间戳（毫秒）
        end_time: 结束时间戳（毫秒）

    Returns:
        所有订单的列表
    """
    all_orders = []
    page = 1
    max_pages = 10  # 防止无限循环

    logger.info(f"开始查询{side}订单，时间范围: {start_time} ~ {end_time}")

    while page <= max_pages:
        params = {
            "page": page,
            "rows": 500,
            "baseAsset": base_asset,
            "quoteAsset": "USDT",
            "side": side,
            "startTime": start_time,
            "endTime": end_time,
        }

        logger.info(f"查询第{page}页{side}订单...")
        response = await api.get_order_history(params)

        if response.get("code") != "000000":
            logger.error(f"查询第{page}页{side}订单失败: {response}")
            break

        orders = response.get("data", [])
        if not orders:
            logger.info(f"第{page}页{side}订单为空，查询结束")
            break

        logger.info(f"第{page}页获取到{len(orders)}个{side}订单")
        all_orders.extend(orders)

        # 如果返回的订单数量少于请求的数量，说明已经是最后一页
        if len(orders) < 500:
            logger.info(f"第{page}页{side}订单数量({len(orders)})少于500，已是最后一页")
            break

        page += 1

    logger.info(f"总共获取到{len(all_orders)}个{side}订单")
    return all_orders


async def get_token_order_history_by_time_range(
    api: AlphaAPI, token_symbol: str
) -> dict:
    """
    使用时间范围查询配置文件指定代币的历史订单

    Args:
        api: API客户端
        token_symbol: 代币符号，如 "CROSS"

    Returns:
        包含订单统计信息的字典
    """
    try:
        # 获取时间范围（以8点为分界的24小时）
        start_time, end_time = get_time_range()

        # 记录查询时间范围
        start_dt = datetime.fromtimestamp(start_time / 1000)
        end_dt = datetime.fromtimestamp(end_time / 1000)
        logger.info(f"查询{token_symbol}订单历史，时间范围: {start_dt} ~ {end_dt}")

        # 根据代币符号映射到base_asset
        token_mapping = {
            "CROSS": "ALPHA_259",
            "MPLX": "ALPHA_XXX",  # 需要根据实际情况填写
            # 可以添加更多代币映射
        }

        base_asset = token_mapping.get(token_symbol)
        if not base_asset:
            logger.error(f"不支持的代币符号: {token_symbol}")
            return {"error": f"不支持的代币符号: {token_symbol}"}

        # 查询买入订单（支持多页合并）
        buy_orders = await fetch_all_orders(
            api, base_asset, "BUY", start_time, end_time
        )

        # 查询卖出订单（支持多页合并）
        sell_orders = await fetch_all_orders(
            api, base_asset, "SELL", start_time, end_time
        )

        # 统计数据
        stats = {
            "token_symbol": token_symbol,
            "base_asset": base_asset,
            "time_range": {
                "start": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "end": end_dt.strftime("%Y-%m-%d %H:%M:%S"),
            },
            "buy_orders": {
                "count": 0,
                "total_amount": 0.0,
                "total_quantity": 0.0,
                "orders": [],
            },
            "sell_orders": {
                "count": 0,
                "total_amount": 0.0,
                "total_quantity": 0.0,
                "orders": [],
            },
        }

        # 处理买入订单
        if buy_orders:
            logger.info(f"找到 {len(buy_orders)} 个买入订单记录")
            for order in buy_orders:
                # 检查订单状态，可能是 "FILLED" 或 "status": "FILLED"
                order_status = order.get("orderStatus") or order.get("status")

                if order_status == "FILLED":
                    price = float(order.get("avgPrice", 0))
                    quantity = float(order.get("executedQty", 0))
                    amount = price * quantity

                    stats["buy_orders"]["count"] += 1
                    stats["buy_orders"]["total_amount"] += amount
                    stats["buy_orders"]["total_quantity"] += quantity
                    stats["buy_orders"]["orders"].append(
                        {
                            "orderId": order.get("orderId"),
                            "price": price,
                            "quantity": quantity,
                            "amount": amount,
                            "time": order.get("time"),
                        }
                    )

        # 处理卖出订单
        if sell_orders:
            logger.info(f"找到 {len(sell_orders)} 个卖出订单记录")
            for order in sell_orders:
                # 检查订单状态，可能是 "FILLED" 或 "status": "FILLED"
                order_status = order.get("orderStatus") or order.get("status")

                if order_status == "FILLED":
                    price = float(order.get("avgPrice", 0))
                    quantity = float(order.get("executedQty", 0))
                    amount = price * quantity

                    stats["sell_orders"]["count"] += 1
                    stats["sell_orders"]["total_amount"] += amount
                    stats["sell_orders"]["total_quantity"] += quantity
                    stats["sell_orders"]["orders"].append(
                        {
                            "orderId": order.get("orderId"),
                            "price": price,
                            "quantity": quantity,
                            "amount": amount,
                            "time": order.get("time"),
                        }
                    )

        # 计算净值
        stats["net_amount"] = (
            stats["buy_orders"]["total_amount"] - stats["sell_orders"]["total_amount"]
        )
        stats["net_quantity"] = (
            stats["buy_orders"]["total_quantity"]
            - stats["sell_orders"]["total_quantity"]
        )

        # 记录统计结果
        logger.info(f"{token_symbol}订单统计:")
        logger.info(
            f"  买入: {stats['buy_orders']['count']}笔, 总额: {stats['buy_orders']['total_amount']:.2f} USDT"
        )
        logger.info(
            f"  卖出: {stats['sell_orders']['count']}笔, 总额: {stats['sell_orders']['total_amount']:.2f} USDT"
        )
        logger.info(f"  净额: {stats['net_amount']:.2f} USDT")

        return stats

    except Exception as e:
        logger.error(f"查询{token_symbol}订单历史失败: {e}")
        return {"error": str(e)}


def decode_dict(d) -> dict[str, str]:
    """辅助函数: 将dict的key/value从bytes转str"""
    if not d:
        return {}
    return {
        k.decode() if isinstance(k, bytes) else k: v.decode()
        if isinstance(v, bytes)
        else v
        for k, v in d.items()
    }


async def load_user_api_params(db_url: str):
    """加载用户API参数"""
    engine = await init_db(db_url)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        users = await get_valid_users(session)
        user_api_params = []

        for user in users:
            headers = decode_dict(user.headers) if user.headers is not None else {}
            cookies = decode_dict(user.cookies) if user.cookies is not None else None

            if not headers:
                logger.warning(f"用户{user.id}缺少认证信息，跳过")
                continue

            api = AlphaAPI(headers=headers, cookies=cookies, user_id=user.id)
            user_api_params.append((user.id, api))

        return user_api_params


def load_config(config_path: str = "config/auto_trader_config.toml") -> dict:
    """加载配置文件"""
    with open(config_path, encoding="utf-8") as f:
        config = toml.load(f)
    return config


async def main():
    """主函数"""
    try:
        # 加载配置
        config = load_config()
        token_symbol = config.get("target_token", "CROSS")

        logger.info("=" * 60)
        logger.info(f"开始查询配置文件指定代币 {token_symbol} 的历史订单")
        logger.info("=" * 60)

        # 加载用户API参数
        db_url = "sqlite+aiosqlite:///data/alpha_users.db"
        user_api_params = await load_user_api_params(db_url)

        if not user_api_params:
            logger.error("没有找到有效的用户API，无法查询订单历史")
            return

        # 使用第一个有效用户的API来查询订单历史
        first_user_id, first_api = user_api_params[0]
        logger.info(f"使用用户{first_user_id}的API查询{token_symbol}订单历史")

        # 查询订单历史统计
        order_stats = await get_token_order_history_by_time_range(
            first_api, token_symbol
        )

        if "error" not in order_stats:
            logger.info("=" * 60)
            logger.info("订单历史查询完成，详细统计:")
            logger.info(
                f"时间范围: {order_stats['time_range']['start']} ~ {order_stats['time_range']['end']}"
            )
            logger.info(f"买入订单: {order_stats['buy_orders']['count']}笔")
            logger.info(
                f"买入总额: {order_stats['buy_orders']['total_amount']:.2f} USDT"
            )
            logger.info(
                f"买入总量: {order_stats['buy_orders']['total_quantity']:.2f} {token_symbol}"
            )
            logger.info(f"卖出订单: {order_stats['sell_orders']['count']}笔")
            logger.info(
                f"卖出总额: {order_stats['sell_orders']['total_amount']:.2f} USDT"
            )
            logger.info(
                f"卖出总量: {order_stats['sell_orders']['total_quantity']:.2f} {token_symbol}"
            )
            logger.info(f"净买入金额: {order_stats['net_amount']:.2f} USDT")
            logger.info(f"净持有量: {order_stats['net_quantity']:.2f} {token_symbol}")
            logger.info("=" * 60)

            # 输出详细订单信息（可选）
            if order_stats["buy_orders"]["orders"]:
                logger.info("买入订单详情:")
                for order in order_stats["buy_orders"]["orders"]:
                    logger.info(
                        f"  订单ID: {order['orderId']}, 价格: {order['price']:.6f}, 数量: {order['quantity']:.2f}, 金额: {order['amount']:.2f}"
                    )

            if order_stats["sell_orders"]["orders"]:
                logger.info("卖出订单详情:")
                for order in order_stats["sell_orders"]["orders"]:
                    logger.info(
                        f"  订单ID: {order['orderId']}, 价格: {order['price']:.6f}, 数量: {order['quantity']:.2f}, 金额: {order['amount']:.2f}"
                    )
        else:
            logger.error(f"查询订单历史失败: {order_stats['error']}")

        # 关闭API连接
        for user_id, api in user_api_params:
            await api.close()

    except Exception as e:
        logger.error(f"脚本执行失败: {e}")


if __name__ == "__main__":
    asyncio.run(main())
