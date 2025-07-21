import asyncio
import json
from pathlib import Path
from alpha_new.api.alpha_api import AlphaAPI
from alpha_new.db.models import init_db
from alpha_new.db.ops import get_user_by_id, get_all_user_ids
from alpha_new.utils import get_script_logger

# 辅助函数: 将dict的key/value从bytes转str
def decode_dict(d) -> dict[str, str]:
    if not d:
        return {}
    return {k.decode() if isinstance(k, bytes) else k: v.decode() if isinstance(v, bytes) else v for k, v in d.items()}

logger = get_script_logger()

async def main():
    # 取第一个用户的headers/cookies用于API（如需更高权限可自定义）
    engine = await init_db("sqlite+aiosqlite:///data/alpha_users.db")
    from sqlalchemy.ext.asyncio import async_sessionmaker
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        user_ids = await get_all_user_ids(session)
        if not user_ids:
            logger.error("数据库无用户，无法获取API凭证")
            return
        user = await get_user_by_id(session, user_ids[0])
        headers = decode_dict(user.headers) if user and user.headers is not None else {}
        cookies = decode_dict(user.cookies) if user and user.cookies is not None else None
        api = AlphaAPI(headers=headers, cookies=cookies)
        data = await api.get_token_list()
        if data.get("code") != "000000":
            logger.error(f"获取币种列表失败: {data}")
            return
        tokens = []
        for item in data["data"]:
            tokens.append({
                "alphaId": item.get("alphaId", ""),
                "symbol": item.get("symbol", ""),
                "name": item.get("name", ""),
                "fullName": item.get("fullName", ""),
                "contractAddress": item.get("contractAddress", ""),
                "decimals": item.get("decimals", ""),
                "chainId": item.get("chainId", ""),
                "chainName": item.get("chainName", ""),
                "logoUrl": item.get("logoUrl", item.get("iconUrl", "")),
            })
        Path("data").mkdir(exist_ok=True)
        with open("data/token_info.json", "w", encoding="utf-8") as f:
            json.dump(tokens, f, ensure_ascii=False, indent=2)
        logger.info(f"已导出 {len(tokens)} 个币种信息到 data/token_info.json")

if __name__ == "__main__":
    asyncio.run(main()) 