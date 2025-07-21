from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .models import User
from ..utils import get_db_logger

logger = get_db_logger()


async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    logger.debug(f"查询用户ID: {user_id}")
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        logger.debug(f"找到用户: {user.name} (ID: {user.id})")
    else:
        logger.warning(f"用户ID {user_id} 不存在")
    return user

async def update_user_info(session: AsyncSession, user_id: int, name: str, email: str, score: int, login_status: str | None = None) -> None:
    logger.info(f"更新用户信息: ID={user_id}, 姓名={name}, 邮箱={email}, 积分={score}, 登录状态={login_status}")
    values = dict(name=name, email=email, score=score)
    if login_status is not None:
        values["login_status"] = login_status
    await session.execute(
        update(User)
        .where(User.id == user_id)
        .values(**values)
    )
    await session.commit()
    logger.debug(f"用户 {user_id} 信息更新完成")

async def get_all_user_ids(session: AsyncSession) -> list[int]:
    logger.debug("查询所有用户ID")
    result = await session.execute(select(User.id))
    user_ids = [row[0] for row in result.fetchall()]
    logger.info(f"找到 {len(user_ids)} 个用户: {user_ids}")
    return user_ids

async def get_user_login_status_stats(session: AsyncSession) -> tuple[int, int]:
    total = await session.execute(select(User.id))
    total_count = len(total.fetchall())
    valid = await session.execute(select(User.id).where(User.login_status == 'valid'))
    valid_count = len(valid.fetchall())
    return total_count, valid_count

async def get_valid_users(session: AsyncSession):
    result = await session.execute(select(User).where(User.login_status == 'valid'))
    return result.scalars().all()
 