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


def save_network_log(
    log_type: str,
    user_id: int | None,
    request_info: dict,
    response_data: dict | None,
    error: str | None = None,
):
    """保存网络请求日志到统一的.log文件"""
    try:
        # 确保logs目录存在
        os.makedirs("logs", exist_ok=True)

        # 统一的日志文件路径
        log_path = "logs/network_requests.log"

        # 格式化时间戳
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        # 构建日志行
        log_line_parts = [
            f"[{timestamp}]",
            f"[{log_type.upper()}]",
            f"[USER:{user_id or 'SYSTEM'}]",
        ]

        # 添加请求信息
        if request_info:
            request_str = " ".join([f"{k}={v}" for k, v in request_info.items()])
            log_line_parts.append(f"REQUEST: {request_str}")

        # 添加响应信息
        if response_data:
            response_str = json.dumps(
                response_data, ensure_ascii=False, separators=(",", ":")
            )
            log_line_parts.append(f"RESPONSE: {response_str}")

        # 添加错误信息
        if error:
            log_line_parts.append(f"ERROR: {error}")

        # 组合完整的日志行
        log_line = " | ".join(log_line_parts) + "\n"

        # 追加写入日志文件
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_line)

        logger.debug(f"💾 网络请求日志已追加到: {log_path}")
    except Exception as e:
        logger.error(f"❌ 保存网络请求日志失败: {e}")


CHECK_INTERVAL = 0.02  # 20ms，更高精度
CONFIG_PATH = "config/airdrop_config.toml"
ADVANCE_MS = 120  # 提前120毫秒发起领取请求，抵消网络延迟


async def get_binance_time() -> datetime:
    async with httpx.AsyncClient() as client:
        try:
            logger.info(f"🌐 请求币安时间API: {BINANCE_TIME_API}")
            request_info = {"url": BINANCE_TIME_API, "method": "GET"}
            resp = await client.get(BINANCE_TIME_API)
            response_data = resp.json()
            logger.info(
                f"📥 币安时间API响应: serverTime={response_data.get('serverTime')}"
            )

            # 保存网络请求日志
            save_network_log("binance_time", None, request_info, response_data)

            server_time = response_data["serverTime"]  # 毫秒
            return datetime.fromtimestamp(server_time / 1000)
        except Exception as e:
            logger.error(f"❌ 币安时间API请求失败: {e}")
            # 保存错误日志
            save_network_log(
                "binance_time",
                None,
                {"url": BINANCE_TIME_API, "method": "GET"},
                None,
                str(e),
            )
            raise


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
    for attempt in range(1, 11):  # 最多查10次
        try:
            logger.info(
                f"🔍 查询空投配置ID (尝试 {attempt}/10): token_symbol={token_symbol}, alpha_id={alpha_id}"
            )
            request_info = {
                "api_method": "query_airdrop_list",
                "token_symbol": token_symbol,
                "alpha_id": alpha_id,
                "attempt": attempt,
            }
            airdrop_list = await api.query_airdrop_list()
            config_count = len(airdrop_list.get("data", {}).get("configs", []))
            logger.info(f"📥 空投列表API响应: 找到{config_count}个配置")

            # 保存网络请求日志
            save_network_log(
                "query_airdrop_list", api.user_id, request_info, airdrop_list
            )

            for config in airdrop_list.get("data", {}).get("configs", []):
                if (token_symbol and config.get("tokenSymbol") == token_symbol) or (
                    alpha_id and config.get("alphaId") == alpha_id
                ):
                    config_id = config.get("configId")
                    logger.info(f"✅ 找到匹配的配置ID: {config_id}")
                    return config_id

            logger.warning(f"⚠️ 第{attempt}次查询未找到匹配的配置")
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.error(f"❌ 查询空投配置ID失败 (尝试 {attempt}/10): {e}")
            # 保存错误日志
            save_network_log(
                "query_airdrop_list",
                api.user_id,
                {"api_method": "query_airdrop_list", "attempt": attempt},
                None,
                str(e),
            )
            await asyncio.sleep(0.5)

    logger.error("❌ 查询配置ID失败，已尝试10次")
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
                logger.info(
                    f"🚀 用户{user_id}发起领取请求 (尝试 {attempt}/{retry_times}): config_id={config_id}"
                )
                request_info = {
                    "api_method": "claim_airdrop",
                    "config_id": config_id,
                    "attempt": attempt,
                    "user_id": user_id,
                }
                result = await api.claim_airdrop(config_id)
                # 记录请求结束时间和延迟
                request_end = time.time()
                network_delay = (request_end - request_start) * 1000  # 转换为毫秒
                logger.info(f"⏱️ 用户{user_id}API请求延迟: {network_delay:.0f}ms")

                # 简化响应日志显示
                result_code = result.get("code", "unknown")
                result_msg = result.get("message", "")
                claim_status = (
                    result.get("data", {}).get("claimStatus", "")
                    if result.get("data")
                    else ""
                )
                logger.info(
                    f"📥 用户{user_id}领取API响应: code={result_code}, message={result_msg}, claimStatus={claim_status}"
                )

                # 保存网络请求日志（包含延迟信息）
                request_info["network_delay_ms"] = network_delay
                save_network_log("claim_airdrop", user_id, request_info, result)

                # 判断领取成功或已领取等终止条件
                if result.get("code") == "000000" or (
                    result.get("data")
                    and result.get("data").get("claimStatus") in ["success", "claimed"]
                ):
                    logger.info(f"✅ 用户{user_id}领取请求成功，停止重试")
                    break
                logger.warning(f"⚠️ 用户{user_id}领取请求未成功，准备重试")
            except Exception as e:
                logger.error(
                    f"❌ 用户{user_id}领取请求异常 (尝试 {attempt}/{retry_times}): {e}"
                )
                # 保存错误日志
                save_network_log(
                    "claim_airdrop",
                    user_id,
                    {
                        "api_method": "claim_airdrop",
                        "config_id": config_id,
                        "attempt": attempt,
                    },
                    None,
                    str(e),
                )
                if attempt == retry_times:
                    return user_id, f"[用户{user_id}] 领取异常: {e}"
            if attempt < retry_times:
                logger.info(f"⏳ 用户{user_id}等待{retry_interval}秒后重试...")
                await asyncio.sleep(retry_interval)

        # 注意：响应数据已通过save_network_log保存到logs/network_requests.log
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
            logger.warning(f"⚠️ 用户{user_id}不存在")
            return 0
        headers = decode_dict(user.headers) if user.headers is not None else {}
        cookies = decode_dict(user.cookies) if user.cookies is not None else None
        api = AlphaAPI(headers=headers, cookies=cookies)
        try:
            logger.info(f"🔍 查询用户{user_id}积分")
            request_info = {"api_method": "get_alpha_score", "user_id": user_id}
            score_data = await api.get_alpha_score()
            score = int(score_data["data"].get("sumScore", 0))
            logger.info(f"📥 用户{user_id}积分API响应: sumScore={score}")

            # 保存网络请求日志
            save_network_log("get_alpha_score", user_id, request_info, score_data)

            logger.info(f"✅ 用户{user_id}当前积分: {score}")
            return score
        except Exception as e:
            logger.error(f"❌ 用户{user_id}查询积分失败: {e}")
            # 保存错误日志
            save_network_log(
                "get_alpha_score",
                user_id,
                {"api_method": "get_alpha_score"},
                None,
                str(e),
            )
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
        log_path = f"logs/claim_results_{log_date}.log"

        # 追加本次结果到日志文件
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n=== 半自动空投领取结果 - {current_time} ===\n")
            for res_uid, msg in claim_results:
                f.write(f"[{current_time}] [USER:{res_uid}] {msg}\n")
            f.write("=" * 50 + "\n")
        # 按用户ID顺序输出
        for uid in sorted(valid_users):
            for res_uid, msg in claim_results:
                if res_uid == uid:
                    print(msg)
                    break


if __name__ == "__main__":
    asyncio.run(main())
