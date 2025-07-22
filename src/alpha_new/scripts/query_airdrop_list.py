import asyncio
import json

from sqlalchemy.ext.asyncio import async_sessionmaker

from alpha_new.api.alpha_api import AlphaAPI
from alpha_new.db.models import init_db
from alpha_new.db.ops import get_user_by_id
from alpha_new.utils import get_script_logger

logger = get_script_logger()


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


async def main(user_id: int) -> None:
    engine = await init_db("sqlite+aiosqlite:///data/alpha_users.db")
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        user = await get_user_by_id(session, user_id)
        if not user:
            logger.error(f"用户{user_id}不存在")
            return
        headers = decode_dict(user.headers) if user.headers is not None else {}
        cookies = decode_dict(user.cookies) if user.cookies is not None else None
        api = AlphaAPI(headers=headers, cookies=cookies, user_id=user_id)

        # 添加重试机制和错误处理
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"正在查询空投列表 (尝试 {attempt}/{max_retries})...")
                airdrop_list = await api.query_airdrop_list()

                # 确保data目录存在
                import os

                os.makedirs("data", exist_ok=True)

                out_path = "data/airdrop_list.json"
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(airdrop_list, f, ensure_ascii=False, indent=2)
                logger.info(f"空投列表已保存到 {out_path}")

                # 显示简要统计信息
                configs = airdrop_list.get("data", {}).get("configs", [])
                logger.info(f"查询成功：找到 {len(configs)} 个空投配置")

                # 显示前几个配置的基本信息
                for i, config in enumerate(configs[:3]):
                    token_symbol = config.get("tokenSymbol", "未知")
                    alpha_id = config.get("alphaId", "未知")
                    logger.info(f"  {i+1}. {token_symbol} ({alpha_id})")

                if len(configs) > 3:
                    logger.info(f"  ... 还有 {len(configs) - 3} 个配置")

                return

            except Exception as e:
                logger.error(f"查询空投列表失败 (尝试 {attempt}/{max_retries}): {e}")
                if attempt == max_retries:
                    logger.error("所有重试都失败了，请检查网络连接或用户认证信息")
                    raise
                logger.info("等待2秒后重试...")
                import asyncio

                await asyncio.sleep(2)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        logger.error(
            "用法: poetry run python -m alpha_new.scripts.query_airdrop_list <user_id>"
        )
    else:
        asyncio.run(main(int(sys.argv[1])))
