#!/usr/bin/env python3
"""
Alpha代币信息模块使用示例
演示如何使用Alpha代币信息API客户端和服务
"""
import asyncio
import logging
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent.parent))

import aiohttp

from src.alpha_new.api_clients.alpha_token_client import AlphaTokenClient
from src.alpha_new.services.alpha_token_service import (
    AlphaTokenService,
)

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def example_basic_usage() -> None:
    """基本用法示例"""
    print("=" * 60)
    print("1. 基本用法示例")
    print("=" * 60)

    async with aiohttp.ClientSession() as session:
        # 创建客户端
        client = AlphaTokenClient(session=session)

        try:
            # 获取所有代币列表
            print("获取Alpha代币列表...")
            token_list = await client.get_token_list()
            print(f"✅ 成功获取 {len(token_list)} 个Alpha代币")

            # 显示前5个代币信息
            print("\n📋 前5个代币信息:")
            for i, token in enumerate(token_list.data[:5], 1):
                print(
                    f"  {i}. {token.symbol} ({token.chain_name}) - 合约: {token.contract_address[:10]}..."
                )

            # 搜索特定代币
            if token_list.data:
                first_token = token_list.data[0]
                print(f"\n🔍 搜索代币: {first_token.symbol}")
                found_token = await client.get_token_by_symbol(first_token.symbol)
                if found_token:
                    print(f"✅ 找到代币: {found_token}")
                else:
                    print("❌ 未找到代币")

            # 显示客户端统计
            stats = client.get_stats()
            print("\n📊 客户端统计:")
            print(f"  - 请求次数: {stats['requests_count']}")
            print(f"  - 缓存命中: {stats['cache_hits']}")
            print(f"  - 错误次数: {stats['errors_count']}")

        except Exception as e:
            print(f"❌ 错误: {e}")


async def example_service_usage() -> None:
    """服务层用法示例"""
    print("\n" + "=" * 60)
    print("2. 服务层用法示例")
    print("=" * 60)

    async with aiohttp.ClientSession() as session:
        # 创建服务
        service = AlphaTokenService(session=session)
        await service.initialize()

        try:
            # 获取所有代币信息
            print("通过服务获取代币信息...")
            all_tokens = await service.get_all_tokens()
            print(f"✅ 服务获取到 {len(all_tokens)} 个代币")

            # 获取链摘要信息
            print("\n📈 获取各链摘要信息...")
            chain_summary = await service.get_chain_summary()
            print("链摘要:")
            for chain_id, summary in list(chain_summary.items())[:3]:  # 只显示前3个链
                print(
                    f"  - 链 {chain_id}: {summary['token_count']} 个代币, 平均供应量: {summary['avg_supply']:.2e}"
                )

            # 获取热门代币
            print("\n🔥 获取热门代币（按供应量排序）:")
            popular_tokens = await service.get_popular_tokens(limit=5)
            for i, token in enumerate(popular_tokens, 1):
                print(f"  {i}. {token.symbol} - 供应量: {token.total_supply}")

            # 批量获取代币信息
            if len(all_tokens.data) >= 3:
                symbols = [token.symbol for token in all_tokens.data[:3]]
                print(f"\n🔄 批量获取代币信息: {symbols}")
                batch_results = await service.batch_get_tokens(symbols)
                for symbol, token_info in batch_results.items():
                    status = "✅" if token_info else "❌"
                    print(
                        f"  {status} {symbol}: {token_info.chain_name if token_info else 'Not found'}"
                    )

            # 显示服务统计
            service_stats = service.get_service_stats()
            print("\n📊 服务统计:")
            print(f"  - 总查询次数: {service_stats['service_stats']['total_queries']}")
            print(f"  - 缓存命中次数: {service_stats['service_stats']['cache_hits']}")
            print(f"  - API调用次数: {service_stats['service_stats']['api_calls']}")
            print(
                f"  - 查询过的唯一符号数: {service_stats['service_stats']['unique_symbols_count']}"
            )

        except Exception as e:
            print(f"❌ 服务错误: {e}")


async def example_search_and_filter() -> None:
    """搜索和过滤示例"""
    print("\n" + "=" * 60)
    print("3. 搜索和过滤示例")
    print("=" * 60)

    async with aiohttp.ClientSession() as session:
        service = AlphaTokenService(session=session)
        await service.initialize()

        try:
            # 获取所有代币用于分析
            all_tokens = await service.get_all_tokens()

            # 获取所有可用的链ID
            available_chains = {token.chain_id for token in all_tokens.data}
            print(f"🔗 可用的链: {list(available_chains)}")

            # 按链ID搜索代币
            if available_chains:
                first_chain = next(iter(available_chains))
                print(f"\n🔍 搜索链 {first_chain} 上的代币:")
                chain_tokens = await service.get_tokens_by_chain(first_chain)
                print(f"✅ 找到 {len(chain_tokens)} 个代币")
                for token in chain_tokens[:3]:  # 只显示前3个
                    print(f"  - {token.symbol}: {token.contract_address}")

            # 按符号模式搜索
            if all_tokens.data:
                # 取第一个代币符号的前3个字符作为搜索模式
                search_pattern = (
                    all_tokens.data[0].symbol[:3] if all_tokens.data[0].symbol else "BR"
                )
                print(f"\n🔍 搜索符号包含 '{search_pattern}' 的代币:")
                pattern_results = await service.search_tokens(
                    symbol_pattern=search_pattern
                )
                print(f"✅ 找到 {len(pattern_results)} 个匹配的代币")
                for token in pattern_results[:3]:
                    print(f"  - {token.symbol} ({token.chain_name})")

            # 复合条件搜索
            if available_chains:
                chain_to_search = next(iter(available_chains))
                print(f"\n🔍 复合搜索：链 {chain_to_search} + 最小供应量:")
                complex_results = await service.search_tokens(
                    chain_id=chain_to_search, min_supply=1000000  # 最小供应量100万
                )
                print(f"✅ 找到 {len(complex_results)} 个符合条件的代币")
                for token in complex_results[:3]:
                    print(f"  - {token.symbol}: 供应量 {token.total_supply}")

        except Exception as e:
            print(f"❌ 搜索错误: {e}")


async def example_caching_and_performance() -> None:
    """缓存和性能示例"""
    print("\n" + "=" * 60)
    print("4. 缓存和性能示例")
    print("=" * 60)

    async with aiohttp.ClientSession() as session:
        service = AlphaTokenService(session=session, cache_duration=60)  # 1分钟缓存
        await service.initialize()

        try:
            # 第一次请求（从API获取）
            print("🕐 第一次请求（从API获取）...")
            start_time = asyncio.get_event_loop().time()
            tokens1 = await service.get_all_tokens()
            first_request_time = asyncio.get_event_loop().time() - start_time
            print(
                f"✅ 第一次请求完成，耗时: {first_request_time:.2f}秒，获取 {len(tokens1)} 个代币"
            )

            # 第二次请求（使用缓存）
            print("\n🕐 第二次请求（使用缓存）...")
            start_time = asyncio.get_event_loop().time()
            tokens2 = await service.get_all_tokens()
            second_request_time = asyncio.get_event_loop().time() - start_time
            print(
                f"✅ 第二次请求完成，耗时: {second_request_time:.2f}秒，获取 {len(tokens2)} 个代币"
            )

            # 性能对比
            if first_request_time > 0:
                speedup = (
                    first_request_time / second_request_time
                    if second_request_time > 0
                    else float("inf")
                )
                print(f"🚀 缓存加速比: {speedup:.1f}x")

            # 强制刷新缓存
            print("\n🔄 强制刷新缓存...")
            start_time = asyncio.get_event_loop().time()
            tokens3 = await service.get_all_tokens(force_refresh=True)
            third_request_time = asyncio.get_event_loop().time() - start_time
            print(
                f"✅ 刷新请求完成，耗时: {third_request_time:.2f}秒，获取 {len(tokens3)} 个代币"
            )

            # 显示缓存统计
            stats = service.get_service_stats()
            print("\n📊 缓存统计:")
            print(f"  - 总查询: {stats['service_stats']['total_queries']}")
            print(f"  - 缓存命中: {stats['service_stats']['cache_hits']}")
            print(f"  - API调用: {stats['service_stats']['api_calls']}")
            cache_hit_rate = (
                stats["service_stats"]["cache_hits"]
                / stats["service_stats"]["total_queries"]
            ) * 100
            print(f"  - 缓存命中率: {cache_hit_rate:.1f}%")

        except Exception as e:
            print(f"❌ 缓存测试错误: {e}")


async def example_error_handling() -> None:
    """错误处理示例"""
    print("\n" + "=" * 60)
    print("5. 错误处理示例")
    print("=" * 60)

    # 使用无效的headers测试错误处理
    invalid_headers = {"User-Agent": "TestAgent/1.0", "Accept": "application/json"}

    async with aiohttp.ClientSession() as session:
        client = AlphaTokenClient(
            session=session,
            headers=invalid_headers,
            max_retries=2,  # 减少重试次数以便快速演示
            retry_delay=0.5,
        )

        try:
            print("🧪 测试错误处理和重试机制...")
            # 这个请求可能会成功，因为API是公开的
            token_list = await client.get_token_list()
            print(f"✅ 请求成功: 获取到 {len(token_list)} 个代币")

            # 显示统计信息，包括任何错误
            stats = client.get_stats()
            print("📊 请求统计:")
            print(f"  - 总请求数: {stats['requests_count']}")
            print(f"  - 错误次数: {stats['errors_count']}")
            print(f"  - 最后请求时间: {stats['last_request_time']}")
            if stats["last_error_time"]:
                print(f"  - 最后错误时间: {stats['last_error_time']}")

        except Exception as e:
            print(f"❌ 捕获到错误: {type(e).__name__}: {e}")
            print("💡 这演示了客户端的错误处理机制")


async def main() -> None:
    """主函数"""
    print("🚀 Alpha代币信息模块使用示例")
    print("=" * 60)

    try:
        # 运行所有示例
        await example_basic_usage()
        await example_service_usage()
        await example_search_and_filter()
        await example_caching_and_performance()
        await example_error_handling()

        print("\n" + "=" * 60)
        print("✅ 所有示例运行完成！")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n❌ 用户中断")
    except Exception as e:
        print(f"\n❌ 运行示例时出错: {e}")
        logger.exception("示例运行失败")


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())
