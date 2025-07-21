#!/usr/bin/env python3
"""
测试优雅退出功能的简单脚本
"""

import asyncio
import signal
import time
from datetime import datetime

# 全局变量
graceful_shutdown = False
shutdown_reason = ""

def signal_handler(signum, frame):
    """信号处理器：处理SIGINT和SIGTERM信号"""
    global graceful_shutdown, shutdown_reason
    signal_names = {signal.SIGINT: "SIGINT (Ctrl+C)", signal.SIGTERM: "SIGTERM"}
    shutdown_reason = signal_names.get(signum, f"Signal {signum}")
    graceful_shutdown = True
    print(f"🛑 接收到退出信号: {shutdown_reason}")
    print("🔄 开始优雅退出流程...")

async def simulate_trading_task(user_id: int, stop_flag: asyncio.Event):
    """模拟交易任务"""
    trade_count = 0
    
    while not stop_flag.is_set():
        trade_count += 1
        print(f"用户{user_id}: 执行第{trade_count}次模拟交易...")
        
        # 模拟买入过程
        print(f"用户{user_id}: 买入中...")
        await asyncio.sleep(2)
        
        # 检查是否需要停止
        if stop_flag.is_set():
            print(f"用户{user_id}: 收到停止信号，当前交易中断")
            break
        
        # 模拟卖出过程
        print(f"用户{user_id}: 卖出中...")
        await asyncio.sleep(2)
        
        # 检查是否需要停止
        if stop_flag.is_set():
            print(f"用户{user_id}: 收到停止信号，当前交易中断")
            break
        
        print(f"用户{user_id}: 完成第{trade_count}次交易")
        
        # 短暂休息
        await asyncio.sleep(1)
    
    print(f"用户{user_id}: 交易任务结束，共完成{trade_count}次交易")

async def main():
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("🚀 启动模拟交易系统")
    print("🔧 优雅退出功能已启用 (Ctrl+C 安全退出)")
    print("=" * 50)
    
    # 创建停止标志
    stop_flag = asyncio.Event()
    
    # 启动多个模拟交易任务
    tasks = []
    for user_id in [1, 2, 3]:
        task = asyncio.create_task(simulate_trading_task(user_id, stop_flag))
        tasks.append(task)
    
    try:
        # 主循环监控
        while not graceful_shutdown and not stop_flag.is_set():
            # 检查所有任务是否完成
            done_tasks = [task for task in tasks if task.done()]
            if len(done_tasks) == len(tasks):
                print("✅ 所有交易任务已完成")
                break
            
            # 短暂等待
            await asyncio.sleep(1)
        
        # 如果收到优雅退出信号
        if graceful_shutdown:
            print(f"🛑 收到退出信号: {shutdown_reason}")
            stop_flag.set()
            
            print("⏳ 等待当前交易完成...")
            # 等待所有任务完成
            await asyncio.gather(*tasks, return_exceptions=True)
        
    except KeyboardInterrupt:
        print("🛑 收到键盘中断信号，开始优雅退出...")
        stop_flag.set()
        
        print("⏳ 等待当前交易完成...")
        await asyncio.gather(*tasks, return_exceptions=True)
        
    except Exception as e:
        print(f"❌ 主循环异常: {e}")
        stop_flag.set()
        
    finally:
        print("🧹 开始清理资源...")
        
        # 取消所有任务
        for task in tasks:
            if not task.done():
                task.cancel()
        
        # 等待任务清理
        try:
            await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=5)
        except asyncio.TimeoutError:
            print("⚠️ 任务清理超时")
        
        print("✅ 资源清理完成")
        print(f"🛑 退出原因: {shutdown_reason}")
        print("👋 程序已安全退出")

if __name__ == "__main__":
    asyncio.run(main())
