#!/usr/bin/env python3
"""
测试用户ID日志记录功能
验证API调用日志中是否正确显示用户ID
"""

import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker

from alpha_new.api.alpha_api import AlphaAPI
from alpha_new.db.models import init_db
from alpha_new.db.ops import get_valid_users
from alpha_new.utils import get_api_logger

logger = get_api_logger()


def decode_dict(d) -> dict[str, str]:
    if not d:
        return {}
    return {
        k.decode() if isinstance(k, bytes) else k: v.decode()
        if isinstance(v, bytes)
        else v
        for k, v in d.items()
    }


async def test_user_id_logging():
    """测试用户ID日志记录功能"""
    logger.info("🧪 开始测试用户ID日志记录功能...")

    # 初始化数据库
    engine = await init_db("sqlite+aiosqlite:///data/alpha_users.db")
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        # 获取所有有效用户
        users = await get_valid_users(session)

        if not users:
            logger.error("❌ 没有找到有效用户，无法进行测试")
            return

        logger.info(f"📋 找到 {len(users)} 个有效用户，开始测试...")

        # 测试每个用户的API调用
        for user in users[:3]:  # 只测试前3个用户
            logger.info(f"🔍 测试用户 {user.id} 的API调用...")

            headers = decode_dict(user.headers) if user.headers is not None else {}
            cookies = decode_dict(user.cookies) if user.cookies is not None else None

            # 创建带用户ID的API实例
            api_with_user_id = AlphaAPI(
                headers=headers, cookies=cookies, user_id=user.id
            )

            # 创建不带用户ID的API实例（对比）
            api_without_user_id = AlphaAPI(headers=headers, cookies=cookies)

            try:
                logger.info("📊 测试带用户ID的API调用:")
                # 测试查询空投列表
                await api_with_user_id.query_airdrop_list(page=1, rows=5)

                logger.info("📊 测试不带用户ID的API调用:")
                # 测试查询空投列表（对比）
                await api_without_user_id.query_airdrop_list(page=1, rows=5)

                logger.info(f"✅ 用户 {user.id} 测试完成")

            except Exception as e:
                logger.error(f"❌ 用户 {user.id} 测试失败: {e}")

            # 关闭API客户端
            await api_with_user_id.close()
            await api_without_user_id.close()

            # 避免请求过于频繁
            await asyncio.sleep(1)

    logger.info("🎉 用户ID日志记录功能测试完成！")
    logger.info("💡 请检查上面的日志输出，确认:")
    logger.info("   1. 带用户ID的API调用日志格式为: [用户X] POST/GET ...")
    logger.info("   2. 不带用户ID的API调用日志格式为: POST/GET ...")


async def main():
    """主函数"""
    await test_user_id_logging()


if __name__ == "__main__":
    asyncio.run(main())
