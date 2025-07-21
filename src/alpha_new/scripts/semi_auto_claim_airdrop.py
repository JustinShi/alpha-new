import asyncio
from datetime import datetime, timedelta
import glob
import json
import os
from pathlib import Path
import time

import httpx
import toml

from alpha_new.api.alpha_api import AlphaAPI
from alpha_new.db.models import init_db
from alpha_new.db.ops import get_user_by_id, get_valid_users
from alpha_new.utils import get_claim_logger

logger = get_claim_logger()

BINANCE_TIME_API = "https://api.binance.com/api/v3/time"
CHECK_INTERVAL = 0.02  # 20ms，更高精度
CONFIG_PATH = "config/airdrop_config.toml"
ADVANCE_MS = 120  # 提前120毫秒发起领取请求，抵消网络延迟


async def get_binance_time() -> datetime:
    async with httpx.AsyncClient() as client:
        resp = await client.get(BINANCE_TIME_API)
        server_time = resp.json()["serverTime"]  # 毫秒
        return datetime.fromtimestamp(server_time / 1000)


def get_next_target_time(hour: int, minute: int, second: int) -> datetime:
    now = datetime.now()
    target = now.replace(hour=hour, minute=minute, second=second, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return target


def decode_dict(d) -> dict[str, str]:
    if not d:
        return {}
    return {
        k.decode() if isinstance(k, bytes) else k: v.decode()
        if isinstance(v, bytes)
        else v
        for k, v in d.items()
    }


async def find_config_id(
    user_id: int, token_symbol: str, alpha_id: str = ""
) -> str | None:
    json_path = Path("data/airdrop_list.json")
    if json_path.exists():
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
            for config in data.get("data", {}).get("configs", []):
                if (token_symbol and config.get("tokenSymbol") == token_symbol) or (
                    alpha_id and config.get("alphaId") == alpha_id
                ):
                    return config.get("configId")
    return None


async def query_config_id(
    api: AlphaAPI, token_symbol: str, alpha_id: str = ""
) -> str | None:
    for _ in range(10):  # 最多查10次
        airdrop_list = await api.query_airdrop_list()
        for config in airdrop_list.get("data", {}).get("configs", []):
            if (token_symbol and config.get("tokenSymbol") == token_symbol) or (
                alpha_id and config.get("alphaId") == alpha_id
            ):
                return config.get("configId")
        await asyncio.sleep(0.5)
    return None


async def calibrate_time_offset(repeat=5):
    offsets = []
    for _ in range(repeat):
        t0 = time.time()
        server_time = (await get_binance_time()).timestamp()
        t1 = time.time()
        local_time = (t0 + t1) / 2
        offsets.append(server_time - local_time)
        await asyncio.sleep(0.1)
    return sum(offsets) / len(offsets)


async def claim_for_user(
    user_id: int,
    token_symbol: str,
    alpha_id: str,
    target_dt: datetime,
    engine,
    retry_times: int = 3,
    retry_interval: int = 1,
    time_offset: float = 0.0,
) -> tuple[int, str]:
    from sqlalchemy.ext.asyncio import async_sessionmaker

    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        user = await get_user_by_id(session, user_id)
        if not user:
            return user_id, f"[用户{user_id}] 不存在"
        headers = decode_dict(user.headers) if user.headers is not None else {}
        cookies = decode_dict(user.cookies) if user.cookies is not None else None
        api = AlphaAPI(headers=headers, cookies=cookies, user_id=user_id)
        config_id = await find_config_id(user_id, token_symbol, alpha_id)
        if not config_id:
            config_id = await query_config_id(api, token_symbol, alpha_id)
        if not config_id:
            return user_id, f"[用户{user_id}] 未查到configId，放弃领取"
        # 毫秒级定时领取（本地+offset判断，提前补偿）
        while True:
            now = datetime.now().timestamp() + time_offset
            delta = target_dt.timestamp() - now
            if delta <= ADVANCE_MS / 1000:
                logger.info(
                    f"[用户{user_id}] 触发领取时刻(本地校准): {datetime.fromtimestamp(now).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}，提前补偿: {ADVANCE_MS}ms"
                )
                break
            await asyncio.sleep(0.005)  # 5ms精度
        result = None
        for attempt in range(1, retry_times + 1):
            try:
                # 记录请求开始时间
                request_start = time.time()
                result = await api.claim_airdrop(config_id)
                # 记录请求结束时间和延迟
                request_end = time.time()
                network_delay = (request_end - request_start) * 1000  # 转换为毫秒
                logger.info(f"[用户{user_id}] API请求延迟: {network_delay:.0f}ms")
                # 判断领取成功或已领取等终止条件
                if result.get("code") == "000000" or (
                    result.get("data")
                    and result.get("data").get("claimStatus") in ["success", "claimed"]
                ):
                    break
            except Exception as e:
                if attempt == retry_times:
                    return user_id, f"[用户{user_id}] 领取异常: {e}"
            if attempt < retry_times:
                await asyncio.sleep(retry_interval)
        # 保存原始返回数据到本地日志
        log_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = f"data/claim_log_{user_id}_{log_time}.json"
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        if result and result.get("code") == "000000":
            return user_id, f"[用户{user_id}] 领取成功"
        msg = result.get("message", "未知错误") if result else "无返回"
        return user_id, f"[用户{user_id}] 领取失败: {msg}"


async def get_user_score(user_id: int, engine) -> int:
    from sqlalchemy.ext.asyncio import async_sessionmaker

    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        user = await get_user_by_id(session, user_id)
        if not user:
            return 0
        headers = decode_dict(user.headers) if user.headers is not None else {}
        cookies = decode_dict(user.cookies) if user.cookies is not None else None
        api = AlphaAPI(headers=headers, cookies=cookies)
        try:
            score_data = await api.get_alpha_score()
            return int(score_data["data"].get("sumScore", 0))
        except Exception as e:
            logger.error(f"[用户{user_id}] 查询积分失败: {e}")
            return 0


async def countdown_loop(target_dt: datetime, time_offset: float):
    last_print = None
    while True:
        now = datetime.now().timestamp() + time_offset
        delta = target_dt.timestamp() - now
        if int(delta) != last_print and delta >= 0:
            logger.info(
                f"[服务器时间(校准)] {datetime.fromtimestamp(now).strftime('%Y-%m-%d %H:%M:%S')} 距目标还剩 {delta:.2f} 秒"
            )
            last_print = int(delta)
        if delta <= 0:
            logger.info("到达目标时间！")
            break
        await asyncio.sleep(CHECK_INTERVAL)


async def main() -> None:
    # 读取配置
    config = toml.load(CONFIG_PATH)
    token_symbol = config.get("token_symbol", "")
    alpha_id = config.get("alpha_id", "")
    hour, minute, second = (
        config.get("target_hour", 19),
        config.get("target_minute", 0),
        config.get("target_second", 0),
    )
    min_score = config.get("min_score", 0)
    claim_retry_times = config.get("claim_retry_times", 3)
    claim_retry_interval = config.get("claim_retry_interval", 1)
    engine = await init_db("sqlite+aiosqlite:///data/alpha_users.db")
    target_dt = get_next_target_time(hour, minute, second)
    logger.info("正在校准本地与服务器时间差...")
    time_offset = await calibrate_time_offset()
    logger.info(f"本地与服务器时间差(本地+offset≈服务器): {time_offset:.3f} 秒")
    # 自动获取所有用户id
    from sqlalchemy.ext.asyncio import async_sessionmaker

    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        users = await get_valid_users(session)
        user_ids = [user.id for user in users]
    logger.info(f"检测到数据库用户: {user_ids}")
    # 查询所有用户积分，筛选达标用户
    logger.info("正在查询所有用户积分...")
    user_score_tasks = [get_user_score(uid, engine) for uid in user_ids]
    scores = await asyncio.gather(*user_score_tasks)
    valid_users = [
        uid for uid, score in zip(user_ids, scores, strict=False) if score >= min_score
    ]
    logger.info(f"达标用户: {valid_users}")
    if not valid_users:
        logger.warning("无用户积分达标，流程结束。")
        return
    # 精确倒计时和并发监控并行
    countdown_task = asyncio.create_task(countdown_loop(target_dt, time_offset))
    claim_task = None
    claim_task_started = False
    while True:
        now = datetime.now().timestamp() + time_offset
        delta = target_dt.timestamp() - now
        if not claim_task_started and delta <= 30:
            logger.info("距离目标时间30秒，启动多用户并发监控...")
            claim_coros = [
                claim_for_user(
                    uid,
                    token_symbol,
                    alpha_id,
                    target_dt,
                    engine,
                    claim_retry_times,
                    claim_retry_interval,
                    time_offset,
                )
                for uid in valid_users
            ]
            claim_task = asyncio.gather(*claim_coros)
            claim_task_started = True
        if delta <= 0:
            break
        await asyncio.sleep(CHECK_INTERVAL)
    await countdown_task
    # 日志自动清理逻辑
    data_dir = "data"
    today = datetime.now().date()
    # 1. 只保留最近7天的合并日志
    keep_days = 7
    for path in glob.glob(os.path.join(data_dir, "claim_log_*.json")):
        # 跳过用户分日志
        if "_" in os.path.basename(path)[10:]:
            continue
        # 提取日期
        try:
            date_str = os.path.basename(path)[10:18]
            file_date = datetime.strptime(date_str, "%Y%m%d").date()
            if (today - file_date).days >= keep_days:
                os.remove(path)
        except Exception:
            pass
    # 2. 删除所有旧的单独用户日志文件（现在统一使用汇总文件）
    logs_dir = "logs"
    for path in glob.glob(os.path.join(logs_dir, "claim_log_*_*.log")):
        os.remove(path)
        logger.info(f"清理旧的单独日志文件: {path}")
    if claim_task:
        claim_results = await claim_task
        # 合并写入单一日志文件
        os.makedirs("logs", exist_ok=True)
        log_date = datetime.now().strftime("%Y%m%d")
        log_path = f"logs/claim_log_{log_date}.log"
        # 读取已有内容
        try:
            with open(log_path, encoding="utf-8") as f:
                all_logs = json.load(f)
        except Exception:
            all_logs = []
        # 追加本次结果
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for res_uid, msg in claim_results:
            all_logs.append(
                {
                    "timestamp": current_time,
                    "user_id": res_uid,
                    "result": msg,
                    "script": "semi_auto_claim_airdrop",
                }
            )
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(all_logs, f, ensure_ascii=False, indent=2)
        # 按用户ID顺序输出
        for uid in sorted(valid_users):
            for res_uid, msg in claim_results:
                if res_uid == uid:
                    print(msg)
                    break


if __name__ == "__main__":
    asyncio.run(main())
