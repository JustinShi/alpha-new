import asyncio
import sys

from sqlalchemy.ext.asyncio import async_sessionmaker

from alpha_new.api.alpha_api import AlphaAPI
from alpha_new.db.ops import get_user_by_id, update_user_info
from alpha_new.utils import decode_dict, get_script_logger, init_db
from alpha_new.utils.config import get_config
from alpha_new.utils.exceptions import (
    AlphaAPIError,
    AuthenticationError,
    DatabaseError,
    UserNotFoundError,
    validate_user_id,
)

logger = get_script_logger()


# decode_dict函数已移至utils.common模块


async def update_user_info_with_api(user_id: int) -> None:
    """
    更新用户信息

    Args:
        user_id: 用户ID

    Raises:
        UserNotFoundError: 用户不存在
        AuthenticationError: 认证失败
        AlphaAPIError: API调用失败
        DatabaseError: 数据库操作失败
    """
    # 获取配置
    config = get_config()

    # 连接数据库
    try:
        engine = await init_db(config.database.url)
        async_session = async_sessionmaker(engine, expire_on_commit=False)
    except Exception as e:
        raise DatabaseError(f"数据库连接失败: {e}", operation="connect")

    async with async_session() as session:
        # 获取用户信息
        try:
            user = await get_user_by_id(session, user_id)
            if not user:
                raise UserNotFoundError(user_id)
        except Exception as e:
            if isinstance(e, UserNotFoundError):
                raise
            raise DatabaseError(f"查询用户失败: {e}", operation="get_user")

        # 准备API认证信息
        headers_data = getattr(user, "headers", None)
        cookies_data = getattr(user, "cookies", None)
        headers = decode_dict(headers_data) if headers_data else {}
        cookies = decode_dict(cookies_data) if cookies_data else None

        if not headers:
            logger.warning(f"用户{user_id}缺少认证头信息")

        # 创建API实例
        api = AlphaAPI(headers=headers, cookies=cookies, user_id=user_id)

        try:
            # 调用API获取最新信息
            logger.info(f"正在获取用户{user_id}的最新信息...")
            user_info = await api.get_user_info()
            alpha_score = await api.get_alpha_score()

            # 解析返回数据
            name = user_info.get("data", {}).get("firstName", "")
            email = user_info.get("data", {}).get("email", "")
            score = int(alpha_score.get("data", {}).get("sumScore", 0))
            login_status = "valid"

            logger.info(f"API调用成功，获取到用户信息: {name}, {email}, 积分: {score}")

        except Exception as e:
            # 处理API错误
            import httpx

            if isinstance(e, httpx.HTTPStatusError):
                if e.response.status_code == 401:
                    logger.error(f"用户{user_id}认证失败，需要重新登录")
                    login_status = "invalid"
                elif e.response.status_code == 429:
                    logger.error(f"用户{user_id}请求频率过高")
                    login_status = "unknown"
                else:
                    logger.error(
                        f"用户{user_id}API调用失败: HTTP {e.response.status_code}"
                    )
                    login_status = "unknown"
            else:
                logger.error(f"用户{user_id}API调用异常: {e}")
                login_status = "unknown"

            # 保持原有信息，只更新状态
            name = getattr(user, "name", "") or ""
            email = getattr(user, "email", "") or ""
            score = getattr(user, "score", 0) or 0

        # 更新数据库
        try:
            await update_user_info(
                session, user_id, name, email, score, login_status=login_status
            )
            logger.info(
                f"用户{user_id}信息已更新: {name}, {email}, {score}, {login_status}"
            )
        except Exception as e:
            raise DatabaseError(f"更新用户信息失败: {e}", operation="update_user")


async def main(user_id: int) -> None:
    """主函数"""
    try:
        await update_user_info_with_api(user_id)
    except UserNotFoundError as e:
        logger.error(f"错误: {e}")
        sys.exit(1)
    except AuthenticationError as e:
        logger.error(f"认证错误: {e}")
        sys.exit(2)
    except AlphaAPIError as e:
        logger.error(f"API错误: {e}")
        sys.exit(3)
    except DatabaseError as e:
        logger.error(f"数据库错误: {e}")
        sys.exit(4)
    except Exception as e:
        logger.error(f"未知错误: {e}")
        sys.exit(5)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.error(
            "用法: poetry run python -m alpha_new.scripts.update_user_info <user_id>"
        )
        logger.error("示例: poetry run python -m alpha_new.scripts.update_user_info 4")
        sys.exit(1)

    try:
        user_id = validate_user_id(sys.argv[1])
        asyncio.run(main(user_id))
    except Exception as e:
        logger.error(f"参数错误: {e}")
        sys.exit(1)
