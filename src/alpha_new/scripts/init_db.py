import asyncio

from alpha_new.db.models import init_db


async def main() -> None:
    await init_db("sqlite+aiosqlite:///data/alpha_users.db")

if __name__ == "__main__":
    asyncio.run(main())
