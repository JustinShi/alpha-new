#!/usr/bin/env python3
"""
网络延迟测试工具
用于测试到币安API的网络延迟，帮助优化advance_ms配置
"""

import asyncio
from datetime import datetime
import statistics
import time

import httpx

from alpha_new.utils import get_claim_logger

logger = get_claim_logger()

BINANCE_TIME_API = "https://api.binance.com/api/v3/time"
CLAIM_API = "https://www.binance.com/bapi/defi/v1/private/wallet-direct/buw/growth/claim-alpha-airdrop"


async def test_api_latency(
    url: str,
    method: str = "GET",
    data: dict = None,
    headers: dict = None,
    test_count: int = 10,
) -> dict:
    """测试API延迟"""
    latencies = []
    success_count = 0

    async with httpx.AsyncClient(timeout=30.0) as client:
        for i in range(test_count):
            try:
                start_time = time.time()

                if method.upper() == "GET":
                    response = await client.get(url, headers=headers)
                elif method.upper() == "POST":
                    response = await client.post(url, json=data, headers=headers)
                else:
                    raise ValueError(f"不支持的HTTP方法: {method}")

                end_time = time.time()
                latency = (end_time - start_time) * 1000  # 转换为毫秒

                if response.status_code < 500:  # 非服务器错误都算成功
                    latencies.append(latency)
                    success_count += 1
                    logger.info(
                        f"测试 {i+1}/{test_count}: {latency:.0f}ms (状态码: {response.status_code})"
                    )
                else:
                    logger.warning(
                        f"测试 {i+1}/{test_count}: 服务器错误 {response.status_code}"
                    )

                # 避免请求过于频繁
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"测试 {i+1}/{test_count}: 请求失败 - {e}")

    if not latencies:
        return {"error": "所有请求都失败了"}

    return {
        "success_rate": success_count / test_count * 100,
        "min_latency": min(latencies),
        "max_latency": max(latencies),
        "avg_latency": statistics.mean(latencies),
        "median_latency": statistics.median(latencies),
        "p95_latency": sorted(latencies)[int(len(latencies) * 0.95)],
        "p99_latency": sorted(latencies)[int(len(latencies) * 0.99)],
        "latencies": latencies,
    }


async def test_time_sync_latency(test_count: int = 10) -> dict:
    """测试时间同步API延迟"""
    logger.info(f"🕐 测试币安时间同步API延迟 (测试{test_count}次)...")
    return await test_api_latency(BINANCE_TIME_API, "GET", test_count=test_count)


async def test_claim_api_latency(headers: dict, test_count: int = 5) -> dict:
    """测试空投领取API延迟 (需要有效的headers)"""
    logger.info(f"🎯 测试空投领取API延迟 (测试{test_count}次)...")
    # 使用无效的config_id进行测试，避免实际领取
    test_data = {"configId": "test_config_id_for_latency_test"}
    return await test_api_latency(CLAIM_API, "POST", test_data, headers, test_count)


def print_latency_report(test_name: str, result: dict):
    """打印延迟测试报告"""
    if "error" in result:
        logger.error(f"❌ {test_name}: {result['error']}")
        return

    logger.info(f"📊 {test_name} 延迟报告:")
    logger.info(f"   成功率: {result['success_rate']:.1f}%")
    logger.info(f"   最小延迟: {result['min_latency']:.0f}ms")
    logger.info(f"   最大延迟: {result['max_latency']:.0f}ms")
    logger.info(f"   平均延迟: {result['avg_latency']:.0f}ms")
    logger.info(f"   中位数延迟: {result['median_latency']:.0f}ms")
    logger.info(f"   95%延迟: {result['p95_latency']:.0f}ms")
    logger.info(f"   99%延迟: {result['p99_latency']:.0f}ms")

    # 建议的advance_ms配置
    recommended_advance_ms = int(
        result["p95_latency"] * 1.5
    )  # 95%延迟的1.5倍作为安全边界
    logger.info(f"💡 建议的advance_ms配置: {recommended_advance_ms}ms")


async def main():
    """主函数"""
    logger.info("🚀 开始网络延迟测试...")
    logger.info(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 测试时间同步API
    time_sync_result = await test_time_sync_latency(10)
    print_latency_report("时间同步API", time_sync_result)

    logger.info("-" * 50)

    # 注意: 空投领取API测试需要有效的用户headers
    logger.info("⚠️  空投领取API测试需要有效的用户认证信息")
    logger.info("   如需测试，请在数据库中配置用户信息后运行完整测试")

    logger.info("✅ 网络延迟测试完成")


if __name__ == "__main__":
    asyncio.run(main())
