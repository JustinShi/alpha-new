import asyncio
from datetime import datetime
import logging
import os

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
import toml
import typer

from alpha_new.db.models import init_db
from alpha_new.db.ops import get_all_user_ids, get_valid_users
from alpha_new.utils import get_cli_logger
from alpha_new.utils.user_session_manager import (
    ensure_valid_users,
    force_refresh_users,
    get_random_valid_user,
    get_user_cache_info,
)

# 在导入任何其他模块之后设置SQLAlchemy日志级别
logging.getLogger("sqlalchemy.engine").setLevel(logging.CRITICAL)
logging.getLogger("sqlalchemy.pool").setLevel(logging.CRITICAL)
logging.getLogger("sqlalchemy.dialects").setLevel(logging.CRITICAL)

logger = get_cli_logger()

QUERY_LOG_PATH = "logs/last_user_query_time.log"


def save_last_query_time():
    os.makedirs("logs", exist_ok=True)
    with open(QUERY_LOG_PATH, "w", encoding="utf-8") as f:
        f.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


def get_last_query_time():
    try:
        with open(QUERY_LOG_PATH, encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return "-"


def get_airdrop_config_info():
    try:
        config = toml.load("config/airdrop_config.toml")
        token_symbol = config.get("token_symbol", "-")
        hour = config.get("target_hour", "-")
        minute = config.get("target_minute", "-")
        second = config.get("target_second", "-")
        min_score = config.get("min_score", "-")
        return token_symbol, f"{hour:02}:{minute:02}:{second:02}", min_score
    except Exception:
        return "-", "-", "-"


def show_main_menu():
    # 只显示主菜单，不再自动更新用户信息
    token_symbol, time_str, min_score = get_airdrop_config_info()
    last_query_time = get_last_query_time()
    from shutil import get_terminal_size

    width = get_terminal_size((80, 20)).columns
    line = "-" * min(60, width)
    # 新增：统计数据库用户数和有效登录数
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from alpha_new.db.models import init_db
    from alpha_new.db.ops import get_user_login_status_stats

    async def get_stats():
        engine = await init_db("sqlite+aiosqlite:///data/alpha_users.db")
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            return await get_user_login_status_stats(session)

    try:
        total_users, valid_users = asyncio.run(get_stats())
        stats_line = f"[bold]总用户:[/bold] {total_users}    [bold green]有效登录:[/bold green] {valid_users}"
    except Exception:
        stats_line = "[red]用户统计获取失败[/red]"
    config_text = (
        f"{line}\n"
        f"  [cyan]空投配置[/cyan]  代币: [bold]{token_symbol}[/bold]    时间: [bold]{time_str}[/bold]    分数阈值: [bold]{min_score}[/bold]"
        f"    [green]最后查询: {last_query_time}[/green]\n"
        f"  {stats_line}\n"
        f"{line}"
    )
    console.print(config_text)
    table = Table(title="Alpha Tools 主菜单", show_lines=True)
    table.add_column("序号", justify="center")
    table.add_column("功能模块", justify="left")
    table.add_row("1", "空投管理")
    table.add_row("2", "交易管理")
    table.add_row("s", "查看用户状态")
    table.add_row("u", "手动更新所有用户")
    table.add_row("q", "退出程序")
    console.print(table)


def show_user_menu():
    table = Table(title="用户查询", show_lines=True)
    table.add_column("序号", justify="center")
    table.add_column("功能", justify="left")
    table.add_row("0", "返回主菜单")
    table.add_row("q", "退出")
    console.print(table)


def show_airdrop_menu():
    table = Table(title="空投管理", show_lines=True)
    table.add_column("序号", justify="center")
    table.add_column("功能", justify="left")
    table.add_row("1", "查询空投列表")
    table.add_row("2", "半自动定时领取")
    table.add_row("3", "全自动领取")
    table.add_row("4", "跳过名单领取空投")
    table.add_row("0", "返回主菜单")
    console.print(table)


def show_trade_menu():
    table = Table(title="交易管理", show_lines=True)
    table.add_column("序号", justify="center")
    table.add_column("功能", justify="left")
    table.add_row("1", "代币信息查询")
    table.add_row("2", "订单历史查询")
    table.add_row("3", "开启自动交易")
    table.add_row("0", "返回主菜单")
    console.print(table)


app = typer.Typer(help="Alpha Tools 命令行工具")
console = Console()


def pick_random_valid_user_id():
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from alpha_new.db.models import init_db

    async def _pick():
        engine = await init_db("sqlite+aiosqlite:///data/alpha_users.db")
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            users = await get_valid_users(session)
            if not users:
                return None
            import random

            return random.choice(users).id

    return asyncio.run(_pick())


@app.command()
def main():
    # 快速启动，不做任何检查
    console.print("[bold green]🚀 Alpha Tools 启动完成[/bold green]")
    console.print("[dim]提示: 功能使用时将自动检查用户状态[/dim]")

    # 主循环
    while True:
        show_main_menu()
        choice = Prompt.ask(
            "请选择功能模块", choices=["1", "2", "s", "u", "q"], default="q"
        )

        if choice == "s":
            # 查看用户状态信息（包含刷新功能）
            show_user_status_with_refresh()
            continue
        if choice == "u":
            # 手动更新所有用户
            asyncio.run(manual_update_all_users())
            continue
        if choice == "1":
            while True:
                show_airdrop_menu()
                airdrop_choice = Prompt.ask(
                    "请选择空投功能",
                    choices=["1", "2", "3", "4", "0", "q"],
                    default="0",
                )
                if airdrop_choice == "1":
                    # 使用智能用户检查
                    user_id = asyncio.run(get_random_valid_user("查询空投列表"))
                    if not user_id:
                        console.print("[red]❌ 没有有效用户，无法查询空投列表[/red]")
                        break

                    console.print(f"[dim]使用用户{user_id}查询空投列表[/dim]")
                    from alpha_new.scripts.query_airdrop_list import main as query_main

                    asyncio.run(query_main(int(user_id)))
                    console.print("[green]✅ 空投列表查询完成[/green]")
                    break
                if airdrop_choice == "2":
                    # 检查有效用户
                    valid_users = asyncio.run(ensure_valid_users("半自动定时领取"))
                    if not valid_users:
                        console.print("[red]❌ 没有有效用户，无法执行领取操作[/red]")
                        break

                    console.print(
                        f"[green]✅ 检测到{len(valid_users)}个有效用户，开始领取流程[/green]"
                    )
                    from alpha_new.scripts.semi_auto_claim_airdrop import (
                        main as claim_main,
                    )

                    asyncio.run(claim_main())
                    console.print("[green]✅ 半自动定时领取流程已执行完毕[/green]")
                    break
                if airdrop_choice == "3":
                    from alpha_new.scripts.auto_claim_airdrop import (
                        main as auto_claim_main,
                    )

                    asyncio.run(auto_claim_main())
                    console.print("[green]✅ 全自动领取流程已执行完毕[/green]")
                    break
                if airdrop_choice == "4":
                    from alpha_new.scripts.skiplist_auto_claim_airdrop import (
                        main as skiplist_claim_main,
                    )

                    asyncio.run(skiplist_claim_main())
                    console.print("[green]✅ 跳过名单领取流程已执行完毕[/green]")
                    break
                if airdrop_choice == "0":
                    break
                if airdrop_choice == "q":
                    console.print(
                        Panel("[cyan]感谢使用 Alpha Tools！[/cyan]", title="退出")
                    )
                    raise typer.Exit()
        elif choice == "2":
            while True:
                show_trade_menu()
                trade_choice = Prompt.ask(
                    "请选择交易功能", choices=["1", "2", "3", "0", "q"], default="0"
                )
                if trade_choice == "1":
                    user_id = pick_random_valid_user_id()
                    if not user_id:
                        console.print("[red]没有有效用户可用于查询代币信息！[/red]")
                        break
                    import json

                    from alpha_new.scripts.export_token_info import (
                        main as export_token_info_main,
                    )

                    asyncio.run(export_token_info_main(user_id))

                    try:
                        with open("data/token_info.json", encoding="utf-8") as f:
                            token_data = json.load(f)

                        # 获取代币列表
                        tokens = (
                            token_data.get("tokens", [])
                            if isinstance(token_data, dict)
                            else token_data
                        )

                        # 统计不同链的代币数量
                        chain_stats: dict[str, int] = {}
                        for token in tokens:
                            chain = token.get("chainName", "Unknown")
                            chain_stats[chain] = chain_stats.get(chain, 0) + 1

                        # 显示统计信息而不是详细列表
                        console.print("[green]📊 代币信息统计:[/green]")
                        console.print(f"[dim]总代币数量: {len(tokens)}[/dim]")
                        console.print(f"[dim]支持的区块链: {len(chain_stats)}个[/dim]")

                        # 显示前5个链的统计
                        sorted_chains = sorted(chain_stats.items(), key=lambda x: x[1], reverse=True)
                        for i, (chain, count) in enumerate(sorted_chains[:5]):
                            console.print(f"[dim]  {chain}: {count}个代币[/dim]")

                        if len(sorted_chains) > 5:
                            console.print(f"[dim]  ... 还有{len(sorted_chains) - 5}个其他链[/dim]")

                        console.print("[dim]详细信息已保存到: data/token_info.json[/dim]")

                    except Exception as e:
                        console.print(f"[red]读取代币信息失败: {e}[/red]")
                    console.print("[green]✅ 代币信息查询已完成[/green]")
                    break
                if trade_choice == "2":
                    from alpha_new.scripts.get_order_history_stats import (
                        main as order_stats_main,
                    )

                    asyncio.run(order_stats_main())
                    console.print("[green]✅ 订单统计已完成[/green]")
                    break
                if trade_choice == "3":
                    from alpha_new.scripts.auto_trader import main as auto_trader_main

                    asyncio.run(auto_trader_main())
                    console.print("[green]✅ 自动交易已启动并执行完毕[/green]")
                    break
                if trade_choice == "0":
                    break
                if trade_choice == "q":
                    console.print(
                        Panel("[cyan]感谢使用 Alpha Tools！[/cyan]", title="退出")
                    )
                    raise typer.Exit()
        elif choice == "q":
            console.print(Panel("[cyan]感谢使用 Alpha Tools！[/cyan]", title="退出"))
            raise typer.Exit()


async def manual_update_all_users():
    """手动更新所有用户"""
    console.print("[yellow]🔄 开始手动更新所有用户信息...[/yellow]")

    from sqlalchemy.ext.asyncio import async_sessionmaker

    from alpha_new.scripts.update_user_info import main as update_main

    try:
        engine = await init_db("sqlite+aiosqlite:///data/alpha_users.db")
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            user_ids = await get_all_user_ids(session)

        if not user_ids:
            console.print("[red]❌ 数据库中没有用户[/red]")
            return

        console.print(f"[dim]📊 发现{len(user_ids)}个用户，开始更新...[/dim]")

        async def update_one(uid):
            max_retries = 3
            for attempt in range(1, max_retries + 1):
                try:
                    await update_main(uid)
                    return True
                except Exception as e:
                    if attempt == max_retries:
                        return str(e)
            return None

        results = await asyncio.gather(*(update_one(uid) for uid in user_ids))

        success_count = 0
        for uid, result in zip(user_ids, results, strict=False):
            if result is True:
                success_count += 1
            # 只显示失败的用户，成功的不显示
            else:
                console.print(f"[red]❌ 用户{uid}更新失败: {result}[/red]")

        console.print(
            f"[green]✅ 更新完成: {success_count}/{len(user_ids)} 成功[/green]"
        )
        save_last_query_time()

    except Exception as e:
        console.print(f"[red]❌ 更新过程中发生错误: {e}[/red]")


def show_user_status_with_refresh():
    """查看用户状态信息（自动刷新）"""
    console.print(Panel("[bold cyan]用户状态信息[/bold cyan]", style="cyan"))

    # 直接刷新用户状态
    console.print("[dim]🔄 正在刷新用户状态...[/dim]")
    force_refresh_users()
    console.print("[green]✨ 用户状态已刷新[/green]")

    # 获取刷新后的状态
    cache_info = get_user_cache_info()

    console.print("\n[dim]当前状态:[/dim]")
    table = Table(title="缓存状态", show_header=True, header_style="bold magenta")
    table.add_column("项目", style="cyan", width=12)
    table.add_column("值", style="green")

    table.add_row(
        "有效用户",
        str(len(cache_info["valid_users"])) if cache_info["valid_users"] else "0",
    )
    table.add_row("最后检查", cache_info["last_check"] or "从未检查")
    table.add_row("缓存有效", "✅ 是" if cache_info["cache_valid"] else "❌ 否")
    table.add_row("最近检查", "✅ 是" if cache_info["recently_checked"] else "❌ 否")

    console.print(table)

    # 显示用户状态结果
    if cache_info["valid_users"]:
        console.print(
            f"\n[green]✅ 当前有 {len(cache_info['valid_users'])} 个有效用户可用[/green]"
        )

        # 显示有效用户列表
        user_table = Table(
            title="有效用户列表", show_header=True, header_style="bold green"
        )
        user_table.add_column("用户ID", style="cyan", justify="center")
        user_table.add_column("状态", style="green", justify="center")

        for user_id in cache_info["valid_users"]:
            user_table.add_row(str(user_id), "✅ 有效")

        console.print(user_table)
    else:
        console.print("\n[red]❌ 没有找到有效用户[/red]")
        console.print("[yellow]💡 建议使用 'u' 选项手动更新所有用户[/yellow]")


if __name__ == "__main__":
    app()
