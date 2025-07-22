"""
代币信息查询脚本
查询并导出用户的代币信息
"""

import asyncio
from datetime import datetime
import json
import os

from sqlalchemy.ext.asyncio import async_sessionmaker

from alpha_new.api.alpha_api import AlphaAPI
from alpha_new.db.models import init_db
from alpha_new.db.ops import get_user_by_id
from alpha_new.utils import decode_dict, get_script_logger

logger = get_script_logger()


async def get_token_info(api: AlphaAPI) -> dict:
    """获取代币信息"""
    try:
        logger.info(f"[用户{api.user_id}] 正在查询代币信息...")

        # 调用真实的API获取代币列表
        response = await api.get_token_list()

        # 解析API响应
        if response.get("code") == "000000" and response.get("data"):
            tokens_data = response["data"]

            # 构建标准化的代币信息结构
            tokens = []
            for token in tokens_data:
                token_info = {
                    "symbol": token.get("symbol", ""),
                    "name": token.get("fullName", token.get("name", "")),
                    "contractAddress": token.get("contractAddress", ""),
                    "chainName": token.get("chainName", ""),
                    "decimals": token.get("decimals", 0),
                    "balance": "0.00000000",  # 余额需要单独查询
                    "usdValue": "0.00",  # USD价值需要单独计算
                    "alphaId": token.get("alphaId", ""),      # 添加alphaId字段
                    "baseAsset": token.get("baseAsset", "")   # 添加baseAsset字段
                }
                tokens.append(token_info)

            result = {
                "timestamp": datetime.now().isoformat(),
                "user_id": api.user_id,
                "tokens": tokens,
                "total_count": len(tokens),
            }

            logger.info(
                f"[用户{api.user_id}] 代币信息查询成功，找到 {len(tokens)} 个代币"
            )
            return result
        # API返回错误
        error_msg = response.get("message", "未知错误")
        logger.error(f"[用户{api.user_id}] API返回错误: {error_msg}")
        raise Exception(f"API返回错误: {error_msg}")

    except Exception as e:
        logger.error(f"[用户{api.user_id}] 代币信息查询失败: {e}")
        raise


async def main(user_id: int) -> None:
    """主函数"""
    try:
        # 初始化数据库
        engine = await init_db("sqlite+aiosqlite:///data/alpha_users.db")
        async_session = async_sessionmaker(engine, expire_on_commit=False)

        async with async_session() as session:
            # 获取用户信息
            user = await get_user_by_id(session, user_id)
            if not user:
                logger.error(f"用户{user_id}不存在")
                return

            # 解码用户认证信息
            headers = decode_dict(user.headers) if user.headers is not None else {}  # type: ignore
            cookies = decode_dict(user.cookies) if user.cookies is not None else None  # type: ignore

            # 创建API实例
            api = AlphaAPI(headers=headers, cookies=cookies, user_id=user_id)

            # 获取代币信息
            token_info = await get_token_info(api)

            # 确保data目录存在
            os.makedirs("data", exist_ok=True)

            # 保存到文件
            output_path = "data/token_info.json"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(token_info, f, ensure_ascii=False, indent=2)

            logger.info(f"代币信息已保存到 {output_path}")

    except Exception as e:
        logger.error(f"代币信息查询失败: {e}")
        raise


if __name__ == "__main__":
    import sys

    user_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1  # 默认用户ID

    asyncio.run(main(user_id))
