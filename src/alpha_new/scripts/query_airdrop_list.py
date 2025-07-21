import asyncio
import json
from sqlalchemy.ext.asyncio import async_sessionmaker
from alpha_new.db.models import init_db
from alpha_new.db.ops import get_user_by_id
from alpha_new.api.alpha_api import AlphaAPI
from alpha_new.utils import get_script_logger

logger = get_script_logger()

# 辅助函数: 将dict的key/value从bytes转str
def decode_dict(d) -> dict[str, str]:
    if not d:
        return {}
    return {k.decode() if isinstance(k, bytes) else k: v.decode() if isinstance(v, bytes) else v for k, v in d.items()}

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
        api = AlphaAPI(headers=headers, cookies=cookies)
        airdrop_list = await api.query_airdrop_list()
        out_path = "data/airdrop_list.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(airdrop_list, f, ensure_ascii=False, indent=2)
        logger.info(f"空投列表已保存到 {out_path}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        logger.error("用法: poetry run python -m alpha_new.scripts.query_airdrop_list <user_id>")
    else:
        asyncio.run(main(int(sys.argv[1]))) 