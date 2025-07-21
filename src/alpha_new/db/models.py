from sqlalchemy import JSON, Column, DateTime, Integer, String, func
from sqlalchemy.ext.asyncio import AsyncAttrs, AsyncEngine, create_async_engine
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class User(AsyncAttrs, Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False)
    email = Column(String(128), nullable=False, unique=True)
    headers = Column(JSON, nullable=True)
    cookies = Column(JSON, nullable=True)
    score = Column(Integer, default=0)
    update_time = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    login_status = Column(String(16), nullable=True, default="unknown")


# 数据库初始化工具
async def init_db(db_url: str) -> AsyncEngine:
    engine = create_async_engine(db_url, echo=True, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine


# 推荐用法:
# engine = await init_db("sqlite+aiosqlite:///data/alpha_users.db")
# async_session = async_sessionmaker(engine, expire_on_commit=False)
