import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker

from alpha_new.api.alpha_api import AlphaAPI
from alpha_new.db.models import init_db
from alpha_new.db.ops import get_user_by_id, update_user_info
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
        try:
            user_info = await api.get_user_info()
            alpha_score = await api.get_alpha_score()
            login_status = "valid"
        except Exception as e:
            import httpx

            if isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 401:
                logger.error(f"用户{user_id}登录失效（401），请重新登录并更新cookies！")
                login_status = "invalid"
            else:
                logger.error(f"用户{user_id}信息获取失败: {e}")
                login_status = "unknown"
            await update_user_info(
                session,
                user_id,
                user.name,
                user.email,
                user.score,
                login_status=login_status,
            )
            return
        # 解析返回数据
        name = user_info["data"].get("firstName", "")
        email = user_info["data"].get("email", "")
        score = int(alpha_score["data"].get("sumScore", 0))
        await update_user_info(
            session, user_id, name, email, score, login_status=login_status
        )
        logger.info(
            f"用户{user_id}信息已更新: {name}, {email}, {score}, {login_status}"
        )


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        logger.error(
            "用法: poetry run python -m alpha_new.scripts.update_user_info <user_id>"
        )
    else:
        asyncio.run(main(int(sys.argv[1])))
