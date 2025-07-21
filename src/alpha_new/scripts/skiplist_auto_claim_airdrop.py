import asyncio
import httpx
import json
import toml
from datetime import datetime, timedelta
from pathlib import Path
from alpha_new.db.models import init_db
from alpha_new.db.ops import get_user_by_id, get_all_user_ids, get_valid_users
from alpha_new.api.alpha_api import AlphaAPI
from alpha_new.utils import get_claim_logger
import time
import os
import glob
import sys

logger = get_claim_logger()

BINANCE_TIME_API = "https://api.binance.com/api/v3/time"
CONFIG_PATH = "config/airdrop_config.toml"

config = toml.load(CONFIG_PATH)

def get_required_config(key, desc=None):
    value = config.get(key, None)
    if value is None or (isinstance(value, str) and value.strip() == ""):
        logger.error(f"配置文件缺少必要参数: {key} ({desc or key})，请在 {CONFIG_PATH} 中填写！")
        sys.exit(1)
    return value

# 配置参数
TARGET_HOUR = int(get_required_config("target_hour", "定时执行小时"))
TARGET_MINUTE = int(get_required_config("target_minute", "定时执行分钟"))
TARGET_SECOND = int(get_required_config("target_second", "定时执行秒数"))
QUERY_INTERVAL = float(get_required_config("query_interval", "查询间隔（秒）"))
QUERY_DURATION = float(get_required_config("query_duration", "查询总时长（秒）"))
CLAIM_RETRY_TIMES = int(get_required_config("claim_retry_times", "领取重试次数"))
CLAIM_RETRY_INTERVAL = float(get_required_config("claim_retry_interval", "领取重试间隔（秒）"))
ADVANCE_MS = int(config.get("advance_ms", 120))  # 可选提前补偿

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
    return {k.decode() if isinstance(k, bytes) else k: v.decode() if isinstance(v, bytes) else v for k, v in d.items()}

async def claim_for_user(user_id: int, engine, target_dt: datetime, time_offset: float = 0.0) -> tuple[int, str]:
    from sqlalchemy.ext.asyncio import async_sessionmaker
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        user = await get_user_by_id(session, user_id)
        if not user:
            return user_id, f"[用户{user_id}] 不存在"
        headers = decode_dict(user.headers) if user.headers is not None else {}
        cookies = decode_dict(user.cookies) if user.cookies is not None else None
        api = AlphaAPI(headers=headers, cookies=cookies)
        # 协程内部等待到目标时间-提前补偿
        while True:
            now = datetime.now().timestamp() + time_offset
            delta = target_dt.timestamp() - now
            if delta <= ADVANCE_MS / 1000:
                logger.info(f"[用户{user_id}] 触发高频查询时刻(本地校准): {datetime.fromtimestamp(now).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}，提前补偿: {ADVANCE_MS}ms")
                break
            await asyncio.sleep(0.01)
        # 高频查询空投列表，发现可领取立即领取
        start_time = time.time()
        claimed = False
        result = None
        last_status = None
        for _ in range(int(QUERY_DURATION // QUERY_INTERVAL)):
            try:
                airdrop_list = await api.query_airdrop_list()
                configs = airdrop_list.get("data", {}).get("configs", [])
                # 只保存“可领取”或状态变化
                status_now = [(cfg.get("configId"), cfg.get("claimInfo", {}).get("claimStatus")) for cfg in configs]
                claimable = [cfg for cfg in configs if (cfg.get("claimInfo", {}) and (cfg.get("claimInfo", {}).get("canClaim") is True or cfg.get("claimInfo", {}).get("claimStatus") == "available"))]
                should_save = False
                if claimable:
                    should_save = True
                elif last_status is not None and status_now != last_status:
                    should_save = True
                if should_save:
                    query_log_time = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                    query_log_path = f"data/airdrop_query_log_{user_id}_{query_log_time}.json"
                    with open(query_log_path, "w", encoding="utf-8") as f:
                        json.dump(airdrop_list, f, ensure_ascii=False, indent=2)
                last_status = status_now
                if claimable:
                    config_id = claimable[0].get("configId")
                    token_symbol = claimable[0].get("tokenSymbol")
                    logger.info(f"[用户{user_id}] 检测到可领取空投: {token_symbol} (configId={config_id})，立即发起领取...")
                    # 多次重试领取
                    for attempt in range(1, CLAIM_RETRY_TIMES + 1):
                        try:
                            result = await api.claim_airdrop(config_id)
                            # 保存每次领取返回原始数据
                            claim_log_time = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                            claim_log_path = f"data/claim_log_{user_id}_{claim_log_time}.json"
                            with open(claim_log_path, "w", encoding="utf-8") as f:
                                json.dump(result, f, ensure_ascii=False, indent=2)
                            code = result.get("code")
                            msg = result.get("message", "无返回信息")
                            claim_info = result.get("data", {}).get("claimInfo", {})
                            status = result.get("data", {}).get("status")
                            # 新增：如果已领取或空投已结束，立即停止重试
                            if (
                                claim_info.get("isClaimed") is True
                                or claim_info.get("claimStatus") == "success"
                                or status == "ended"
                            ):
                                logger.info(f"[用户{user_id}] 空投 {token_symbol} 已领取或已结束，停止重试。")
                                break
                            if code == "000000":
                                logger.info(f"[用户{user_id}] 空投 {token_symbol} 领取成功！（第{attempt}次尝试）")
                                claimed = True
                                break
                            else:
                                if attempt == CLAIM_RETRY_TIMES:
                                    logger.warning(f"[用户{user_id}] 空投 {token_symbol} 领取失败: {msg}")
                        except Exception as e:
                            if attempt == CLAIM_RETRY_TIMES:
                                logger.error(f"[用户{user_id}] 空投 {token_symbol} 领取异常: {e}")
                        if (
                            claim_info.get("isClaimed") is True
                            or claim_info.get("claimStatus") == "success"
                            or status == "ended"
                        ):
                            break
                        if attempt < CLAIM_RETRY_TIMES:
                            await asyncio.sleep(CLAIM_RETRY_INTERVAL)
                    break  # 只要有一个可领取就停止高频查询
            except Exception as e:
                logger.error(f"[用户{user_id}] 查询空投列表异常: {e}")
            await asyncio.sleep(QUERY_INTERVAL)
            if time.time() - start_time > QUERY_DURATION:
                break
        # 保存最后一次领取返回数据到本地日志（兼容原有逻辑）
        log_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = f"data/claim_log_{user_id}_{log_time}.json"
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        if claimed and result and result.get("code") == "000000":
            return user_id, f"[用户{user_id}] 领取成功"
        else:
            msg = result.get("message", "未检测到可领取空投或领取失败") if result else "无返回"
            return user_id, f"[用户{user_id}] 领取失败: {msg}"

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

async def countdown_loop(target_dt, time_offset):
    last_print = None
    while True:
        now = datetime.now().timestamp() + time_offset
        delta = target_dt.timestamp() - now
        if int(delta) != last_print and delta >= 0:
            logger.info(f"[服务器时间(校准)] {datetime.fromtimestamp(now).strftime('%Y-%m-%d %H:%M:%S')} 距目标还剩 {delta:.2f} 秒")
            last_print = int(delta)
        if delta <= 0:
            logger.info("到达目标时间！")
            break
        await asyncio.sleep(0.2)

async def find_first_claimable_config_id(users, engine, token_symbol):
    from sqlalchemy.ext.asyncio import async_sessionmaker
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async def query_one(user):
        headers = decode_dict(user.headers) if user.headers is not None else {}
        cookies = decode_dict(user.cookies) if user.cookies is not None else None
        api = AlphaAPI(headers=headers, cookies=cookies)
        try:
            airdrop_list = await api.query_airdrop_list()
            for cfg in airdrop_list.get("data", {}).get("configs", []):
                if cfg.get("tokenSymbol") == token_symbol and (
                    cfg.get("claimInfo", {}).get("canClaim") or cfg.get("claimInfo", {}).get("claimStatus") == "available"
                ):
                    return cfg.get("configId")
        except Exception:
            pass
        return None
    tasks = [query_one(user) for user in users]
    results = await asyncio.gather(*tasks)
    config_ids = [cfg for cfg in results if cfg]
    return config_ids[0] if config_ids else None

async def main():
    # 读取配置
    token_symbol = config.get("token_symbol", "")
    alpha_id = config.get("alpha_id", "")
    hour, minute, second = TARGET_HOUR, TARGET_MINUTE, TARGET_SECOND
    engine = await init_db("sqlite+aiosqlite:///data/alpha_users.db")
    target_dt = get_next_target_time(hour, minute, second)
    logger.info("正在校准本地与服务器时间差...")
    time_offset = await calibrate_time_offset()
    logger.info(f"本地与服务器时间差(本地+offset≈服务器): {time_offset:.3f} 秒")
    # 自动获取所有有效用户
    from sqlalchemy.ext.asyncio import async_sessionmaker
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        users = await get_valid_users(session)
        user_ids = [user.id for user in users]
    logger.info(f"检测到数据库有效用户: {user_ids}")
    # 等待到目标时间
    pre_wait = target_dt.timestamp() - 30 - datetime.now().timestamp()
    if pre_wait > 0:
        logger.info(f"提前30秒启动所有用户协程，等待 {pre_wait:.2f} 秒...")
        countdown_task = asyncio.create_task(countdown_loop(target_dt, time_offset))
        await asyncio.sleep(pre_wait)
        await countdown_task
    else:
        logger.warning("目标时间已过，立即启动！")
    # 1. 并发查询所有用户的空投列表，只要有一个查到configId，所有用户都领取
    config_id = await find_first_claimable_config_id(users, engine, token_symbol)
    if not config_id:
        logger.warning(f"没有用户查到可领取空投({token_symbol})，流程结束。")
        return
    logger.info(f"检测到可领取空投({token_symbol})，configId={config_id}，所有用户开始领取...")
    # 2. 并发领取
    async def claim_for_user(user):
        headers = decode_dict(user.headers) if user.headers is not None else {}
        cookies = decode_dict(user.cookies) if user.cookies is not None else None
        api = AlphaAPI(headers=headers, cookies=cookies)
        result = None
        for attempt in range(1, CLAIM_RETRY_TIMES + 1):
            try:
                result = await api.claim_airdrop(config_id)
                if result.get("code") == "000000" or (result.get("data") and result.get("data").get("claimStatus") in ["success", "claimed"]):
                    break
            except Exception as e:
                if attempt == CLAIM_RETRY_TIMES:
                    return user.id, f"[用户{user.id}] 领取异常: {e}"
            if attempt < CLAIM_RETRY_TIMES:
                await asyncio.sleep(CLAIM_RETRY_INTERVAL)
        # 保存原始返回数据到本地日志
        log_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = f"data/claim_log_{user.id}_{log_time}.json"
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        if result and result.get("code") == "000000":
            return user.id, f"[用户{user.id}] 领取成功"
        else:
            msg = result.get("message", "未知错误") if result else "无返回"
            return user.id, f"[用户{user.id}] 领取失败: {msg}"
    claim_results = await asyncio.gather(*(claim_for_user(user) for user in users))
    # 合并写入单一日志文件
    log_date = datetime.now().strftime("%Y%m%d")
    log_path = f"data/claim_log_{log_date}.json"
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            all_logs = json.load(f)
    except Exception:
        all_logs = []
    for res_uid, msg in claim_results:
        all_logs.append({"user_id": res_uid, "result": msg})
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(all_logs, f, ensure_ascii=False, indent=2)
    # 按用户ID顺序输出
    for user in sorted(users, key=lambda u: u.id):
        for res_uid, msg in claim_results:
            if res_uid == user.id:
                print(msg)
                break

if __name__ == "__main__":
    asyncio.run(main()) 