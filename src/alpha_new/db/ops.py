from sqlalchemy import and_, case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..utils import get_db_logger
from .models import User

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


async def update_user_info(
    session: AsyncSession,
    user_id: int,
    name: str,
    email: str,
    score: int,
    login_status: str | None = None,
) -> None:
    logger.info(
        f"更新用户信息: ID={user_id}, 姓名={name}, 邮箱={email}, 积分={score}, 登录状态={login_status}"
    )
    values = {"name": name, "email": email, "score": score}
    if login_status is not None:
        values["login_status"] = login_status
    await session.execute(update(User).where(User.id == user_id).values(**values))
    await session.commit()
    logger.debug(f"用户 {user_id} 信息更新完成")


async def get_all_user_ids(session: AsyncSession) -> list[int]:
    logger.debug("查询所有用户ID")
    result = await session.execute(select(User.id))
    user_ids = [row[0] for row in result.fetchall()]
    logger.info(f"找到 {len(user_ids)} 个用户: {user_ids}")
    return user_ids


async def get_user_login_status_stats(session: AsyncSession) -> tuple[int, int]:
    """
    获取用户登录状态统计（优化版本）
    使用聚合查询替代多次查询
    """
    # 🚀 优化：使用单个聚合查询替代多次查询
    result = await session.execute(
        select(
            func.count().label("total"),
            func.sum(case((User.login_status == "valid", 1), else_=0)).label("valid"),
        )
    )
    row = result.first()
    total_count = row.total if row else 0
    valid_count = row.valid if row else 0

    logger.debug(f"用户统计: 总数={total_count}, 有效={valid_count}")
    return total_count, valid_count


async def get_valid_users(session: AsyncSession) -> list[User]:
    """获取有效用户列表（优化版本）"""
    # 🚀 优化：使用索引查询，添加排序
    result = await session.execute(
        select(User)
        .where(User.login_status == "valid")
        .order_by(User.score.desc(), User.update_time.desc())  # 按积分和更新时间排序
    )
    users = result.scalars().all()
    logger.debug(f"找到{len(users)}个有效用户")
    return users


async def get_users_by_score_range(
    session: AsyncSession, min_score: int = 0, max_score: int | None = None
) -> list[User]:
    """
    根据积分范围获取用户（优化版本）

    Args:
        session: 数据库会话
        min_score: 最小积分
        max_score: 最大积分（可选）

    Returns:
        用户列表
    """
    # 🚀 优化：使用复合索引查询
    query = select(User).where(
        and_(User.login_status == "valid", User.score >= min_score)
    )

    if max_score is not None:
        query = query.where(User.score <= max_score)

    query = query.order_by(User.score.desc())

    result = await session.execute(query)
    users = result.scalars().all()

    logger.debug(f"积分范围[{min_score}, {max_score}]找到{len(users)}个用户")
    return users


async def get_users_batch(session: AsyncSession, user_ids: list[int]) -> list[User]:
    """
    批量获取用户信息（优化版本）

    Args:
        session: 数据库会话
        user_ids: 用户ID列表

    Returns:
        用户列表
    """
    if not user_ids:
        return []

    # 🚀 优化：使用IN查询批量获取
    result = await session.execute(
        select(User).where(User.id.in_(user_ids)).order_by(User.id)  # 保持顺序
    )
    users = result.scalars().all()

    logger.debug(f"批量查询{len(user_ids)}个用户，找到{len(users)}个")
    return users


async def update_users_batch(
    session: AsyncSession, updates: list[tuple[int, dict]]
) -> int:
    """
    批量更新用户信息（优化版本）

    Args:
        session: 数据库会话
        updates: 更新列表，格式为[(user_id, update_dict), ...]

    Returns:
        更新的用户数量
    """
    if not updates:
        return 0

    updated_count = 0

    # 🚀 优化：批量更新
    for user_id, update_data in updates:
        result = await session.execute(
            update(User).where(User.id == user_id).values(**update_data)
        )
        updated_count += result.rowcount

    await session.commit()
    logger.info(f"批量更新{updated_count}个用户")
    return updated_count


async def get_user_stats_summary(session: AsyncSession) -> dict:
    """
    获取用户统计摘要（优化版本）

    Returns:
        统计信息字典
    """
    # 🚀 优化：单个查询获取所有统计信息
    result = await session.execute(
        select(
            func.count().label("total_users"),
            func.sum(case((User.login_status == "valid", 1), else_=0)).label(
                "valid_users"
            ),
            func.sum(case((User.login_status == "invalid", 1), else_=0)).label(
                "invalid_users"
            ),
            func.sum(case((User.login_status == "unknown", 1), else_=0)).label(
                "unknown_users"
            ),
            func.avg(User.score).label("avg_score"),
            func.max(User.score).label("max_score"),
            func.min(User.score).label("min_score"),
            func.max(User.update_time).label("last_update"),
        )
    )

    row = result.first()

    stats = {
        "total_users": row.total_users or 0,
        "valid_users": row.valid_users or 0,
        "invalid_users": row.invalid_users or 0,
        "unknown_users": row.unknown_users or 0,
        "avg_score": float(row.avg_score) if row.avg_score else 0.0,
        "max_score": row.max_score or 0,
        "min_score": row.min_score or 0,
        "last_update": row.last_update,
    }

    logger.debug(f"用户统计摘要: {stats}")
    return stats
