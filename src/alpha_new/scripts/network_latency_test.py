#!/usr/bin/env python3
"""
增强的网络延迟测试工具
用于测试到币安API的网络延迟，提供自动调优和优化建议
"""

import asyncio
from datetime import datetime
import json
import os
import statistics
import time

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from alpha_new.db.models import init_db
from alpha_new.db.ops import get_user_by_id
from alpha_new.utils import get_claim_logger
from alpha_new.utils.network_optimizer import (
    DynamicLatencyOptimizer,
    LatencyConfig,
    get_latency_optimizer,
)

logger = get_claim_logger()
console = Console()

BINANCE_TIME_API = "https://api.binance.com/api/v3/time"
CLAIM_API = "https://www.binance.com/bapi/defi/v1/private/wallet-direct/buw/growth/claim-alpha-airdrop"


async def test_api_latency(
    url: str,
    method: str = "GET",
    data: dict | None = None,
    headers: dict | None = None,
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


async def enhanced_latency_test(user_id: int | None = None, save_results: bool = True):
    """增强的延迟测试，使用动态优化器"""
    console.print(Panel("🚀 增强网络延迟测试", style="bold green"))

    # 获取用户认证信息（如果提供了user_id）
    headers = None
    if user_id:
        try:
            engine = await init_db("sqlite+aiosqlite:///data/alpha_users.db")
            from sqlalchemy.ext.asyncio import async_sessionmaker

            async_session = async_sessionmaker(engine, expire_on_commit=False)
            async with async_session() as session:
                user = await get_user_by_id(session, user_id)
                if user and user.headers:
                    headers = {
                        k.decode() if isinstance(k, bytes) else k: v.decode()
                        if isinstance(v, bytes)
                        else v
                        for k, v in user.headers.items()
                    }
                    console.print(f"✅ 使用用户 {user_id} 的认证信息")
        except Exception as e:
            logger.warning(f"获取用户认证信息失败: {e}")

    # 创建延迟优化器
    config = LatencyConfig(
        test_interval=60,
        max_latency_threshold=5000.0,
        history_size=50,
        min_test_count=5,
    )
    optimizer = DynamicLatencyOptimizer(config)

    # 执行自动调优
    console.print("🔧 执行自动延迟调优...")
    optimal_advance_ms = await optimizer.auto_tune_advance_ms(headers)

    # 获取详细统计信息
    all_stats = optimizer.get_all_stats()

    # 显示结果
    display_enhanced_results(all_stats, optimal_advance_ms)

    # 生成优化报告
    report = optimizer.get_optimization_report()
    display_optimization_report(report)

    # 保存结果到文件
    if save_results:
        await save_test_results(report, user_id)

    return report


def display_enhanced_results(stats: dict, optimal_advance_ms: int):
    """显示增强的测试结果"""
    if not stats:
        console.print("⚠️ 没有可用的测试数据", style="yellow")
        return

    # 创建结果表格
    table = Table(title="网络延迟测试结果")
    table.add_column("端点", style="cyan")
    table.add_column("平均延迟", justify="right", style="green")
    table.add_column("P95延迟", justify="right", style="yellow")
    table.add_column("成功率", justify="right", style="blue")
    table.add_column("测试次数", justify="right")

    for endpoint_key, stat in stats.items():
        table.add_row(
            endpoint_key,
            f"{stat.avg_latency:.0f}ms",
            f"{stat.p95_latency:.0f}ms",
            f"{stat.success_rate:.1f}%",
            str(stat.test_count),
        )

    console.print(table)

    # 显示最优配置
    console.print(
        Panel(
            f"💡 建议的advance_ms配置: [bold green]{optimal_advance_ms}ms[/bold green]",
            title="优化建议",
            style="blue",
        )
    )


def display_optimization_report(report: dict):
    """显示优化报告"""
    if report["status"] == "no_data":
        console.print(f"⚠️ {report['message']}", style="yellow")
        return

    # 显示总体统计
    overall = report["overall_stats"]
    console.print(
        Panel(
            f"平均延迟: {overall['avg_latency']:.0f}ms\n"
            f"成功率: {overall['success_rate']:.1f}%\n"
            f"总测试次数: {overall['total_tests']}",
            title="总体统计",
            style="cyan",
        )
    )

    # 显示建议
    if report["recommendations"]:
        recommendations_text = "\n".join(
            f"• {rec}" for rec in report["recommendations"]
        )
        console.print(Panel(recommendations_text, title="优化建议", style="yellow"))


async def save_test_results(report: dict, user_id: int | None = None):
    """保存测试结果到文件"""
    try:
        os.makedirs("data/latency_tests", exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"data/latency_tests/latency_test_{timestamp}"
        if user_id:
            filename += f"_user{user_id}"
        filename += ".json"

        # 准备保存的数据
        save_data = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "report": report,
        }

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2, default=str)

        console.print(f"📁 测试结果已保存到: {filename}", style="dim")

    except Exception as e:
        logger.error(f"保存测试结果失败: {e}")


async def continuous_monitoring(duration_minutes: int = 60, user_id: int | None = None):
    """连续监控网络延迟"""
    console.print(Panel(f"🔄 开始连续监控 {duration_minutes} 分钟", style="bold blue"))

    # 获取用户认证信息
    headers = None
    if user_id:
        try:
            engine = await init_db("sqlite+aiosqlite:///data/alpha_users.db")
            from sqlalchemy.ext.asyncio import async_sessionmaker

            async_session = async_sessionmaker(engine, expire_on_commit=False)
            async with async_session() as session:
                user = await get_user_by_id(session, user_id)
                if user and user.headers:
                    headers = {
                        k.decode() if isinstance(k, bytes) else k: v.decode()
                        if isinstance(v, bytes)
                        else v
                        for k, v in user.headers.items()
                    }
        except Exception as e:
            logger.warning(f"获取用户认证信息失败: {e}")

    # 创建优化器并启动监控
    optimizer = get_latency_optimizer()
    await optimizer.start_background_monitoring(headers)

    try:
        # 等待指定时间
        await asyncio.sleep(duration_minutes * 60)
    finally:
        # 停止监控
        await optimizer.stop_background_monitoring()

    # 显示最终结果
    report = optimizer.get_optimization_report()
    display_optimization_report(report)

    console.print("✅ 连续监控完成", style="bold green")


async def legacy_test():
    """兼容模式：原始测试功能"""
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


async def main():
    """主函数"""
    console.print(Panel("🚀 增强网络延迟测试工具", style="bold green"))

    # 显示菜单
    console.print("\n选择测试模式:")
    console.print("1. 基础延迟测试（无认证）")
    console.print("2. 完整延迟测试（需要用户ID）")
    console.print("3. 连续监控模式")
    console.print("4. 兼容模式（原始测试）")

    try:
        choice = input("\n请选择 (1-4): ").strip()

        if choice == "1":
            await enhanced_latency_test()
        elif choice == "2":
            user_id = input("请输入用户ID: ").strip()
            if user_id.isdigit():
                await enhanced_latency_test(int(user_id))
            else:
                console.print("❌ 无效的用户ID", style="red")
        elif choice == "3":
            duration = input("监控时长（分钟，默认60）: ").strip()
            duration_minutes = int(duration) if duration.isdigit() else 60
            user_id = input("用户ID（可选）: ").strip()
            user_id = int(user_id) if user_id.isdigit() else None
            await continuous_monitoring(duration_minutes, user_id)
        elif choice == "4":
            await legacy_test()
        else:
            console.print("❌ 无效选择", style="red")

    except KeyboardInterrupt:
        console.print("\n⏹️ 用户中断测试", style="yellow")
    except Exception as e:
        console.print(f"❌ 测试过程中出错: {e}", style="red")
        logger.error(f"测试异常: {e}")


if __name__ == "__main__":
    asyncio.run(main())
