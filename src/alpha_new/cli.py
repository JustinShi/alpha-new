import asyncio
from datetime import datetime
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
    # 程序启动时自动并发更新一次所有用户信息
    import asyncio

    from sqlalchemy.ext.asyncio import async_sessionmaker

    from alpha_new.scripts.update_user_info import main as update_main

    async def update_all_users_concurrent():
        engine = await init_db("sqlite+aiosqlite:///data/alpha_users.db")
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            user_ids = await get_all_user_ids(session)
        logger.info(f"自动检测到用户: {user_ids}，开始并发更新...")

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
        for uid, result in zip(user_ids, results, strict=False):
            if result is True:
                logger.info(f"用户 {uid} 信息已更新。")
            else:
                logger.error(f"用户 {uid} 更新失败: {result}")
        save_last_query_time()

    asyncio.run(update_all_users_concurrent())
    # 主循环
    while True:
        show_main_menu()
        choice = Prompt.ask("请选择功能模块", choices=["1", "2", "q", "r"], default="q")
        if choice == "r":
            console.print("[cyan]配置已刷新！[/cyan]")
            continue  # 重新显示主菜单
        if choice == "1":
            while True:
                show_airdrop_menu()
                airdrop_choice = Prompt.ask(
                    "请选择空投功能",
                    choices=["1", "2", "3", "4", "0", "q"],
                    default="0",
                )
                if airdrop_choice == "1":
                    user_id = pick_random_valid_user_id()
                    if not user_id:
                        console.print("[red]没有有效用户可用于查询空投列表！[/red]")
                        break
                    from alpha_new.scripts.query_airdrop_list import main as query_main

                    asyncio.run(query_main(int(user_id)))
                    console.print(
                        Panel(
                            "[green]空投列表查询完成，返回空投管理菜单。[/green]",
                            title="空投列表",
                        )
                    )
                    break
                if airdrop_choice == "2":
                    from alpha_new.scripts.semi_auto_claim_airdrop import (
                        main as claim_main,
                    )

                    asyncio.run(claim_main())
                    console.print(
                        Panel(
                            "[green]半自动定时领取流程已执行完毕。返回空投管理菜单。[/green]",
                            title="半自动定时领取",
                        )
                    )
                    break
                if airdrop_choice == "3":
                    from alpha_new.scripts.auto_claim_airdrop import (
                        main as auto_claim_main,
                    )

                    asyncio.run(auto_claim_main())
                    console.print(
                        Panel(
                            "[green]全自动领取流程已执行完毕。返回空投管理菜单。[/green]",
                            title="全自动领取",
                        )
                    )
                    break
                if airdrop_choice == "4":
                    from alpha_new.scripts.skiplist_auto_claim_airdrop import (
                        main as skiplist_claim_main,
                    )

                    asyncio.run(skiplist_claim_main())
                    console.print(
                        Panel(
                            "[green]跳过名单领取流程已执行完毕。返回空投管理菜单。[/green]",
                            title="跳过名单领取空投",
                        )
                    )
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
                    from rich.table import Table

                    try:
                        with open("data/token_info.json", encoding="utf-8") as f:
                            tokens = json.load(f)
                        table = Table(title="代币信息列表")
                        table.add_column("简称", justify="left")
                        table.add_column("全称", justify="left")
                        table.add_column("合约地址", justify="left")
                        table.add_column("链", justify="left")
                        table.add_column("精度", justify="right")
                        for t in tokens:
                            table.add_row(
                                t.get("symbol", ""),
                                t.get("fullName", t.get("name", "")),
                                t.get("contractAddress", ""),
                                t.get("chainName", ""),
                                str(t.get("decimals", "")),
                            )
                        console.print(table)
                    except Exception as e:
                        console.print(f"[red]读取代币信息失败: {e}[/red]")
                    console.print(
                        Panel(
                            "[green]代币信息查询已完成，返回交易管理菜单。[/green]",
                            title="代币信息查询",
                        )
                    )
                    break
                if trade_choice == "2":
                    from alpha_new.scripts.get_order_history_stats import (
                        main as order_stats_main,
                    )

                    asyncio.run(order_stats_main())
                    console.print(
                        Panel(
                            "[green]订单统计已完成，返回交易管理菜单。[/green]",
                            title="订单历史查询",
                        )
                    )
                    break
                if trade_choice == "3":
                    from alpha_new.scripts.auto_trader import main as auto_trader_main

                    asyncio.run(auto_trader_main())
                    console.print(
                        Panel(
                            "[green]自动交易已启动并执行完毕，返回交易管理菜单。[/green]",
                            title="自动交易",
                        )
                    )
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


if __name__ == "__main__":
    app()
