"""
日志管理脚本
提供日志查看、清理、级别调整等功能
"""

import os
import sys
import glob
from pathlib import Path
from datetime import datetime
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt

app = typer.Typer(help="日志管理工具")
console = Console()

def get_log_files() -> list[Path]:
    """获取所有日志文件"""
    # 尝试多个可能的路径
    possible_paths = [
        Path(__file__).parent.parent.parent / "logs",  # 从脚本文件相对路径
        Path.cwd() / "logs",  # 当前工作目录
        Path.home() / "alpha-new" / "logs",  # 用户主目录
    ]
    
    for logs_dir in possible_paths:
        if logs_dir.exists():
            log_files = []
            for pattern in ["*.log", "*.txt"]:
                log_files.extend(logs_dir.glob(pattern))
            if log_files:
                return sorted(log_files, key=lambda x: x.stat().st_mtime, reverse=True)
    
    return []

def format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    size = float(size_bytes)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"

def show_log_files():
    """显示日志文件列表"""
    log_files = get_log_files()
    
    if not log_files:
        console.print(Panel("[yellow]未找到日志文件[/yellow]", title="日志文件"))
        return
    
    table = Table(title="日志文件列表", show_lines=True)
    table.add_column("序号", justify="center")
    table.add_column("文件名", justify="left")
    table.add_column("大小", justify="right")
    table.add_column("修改时间", justify="center")
    
    for i, log_file in enumerate(log_files, 1):
        stat = log_file.stat()
        size = format_file_size(stat.st_size)
        mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        table.add_row(str(i), log_file.name, size, mtime)
    
    console.print(table)
    return log_files

@app.command()
def list():
    """列出所有日志文件"""
    show_log_files()

@app.command()
def view(
    file_name: str = typer.Argument(..., help="日志文件名"),
    lines: int = typer.Option(50, "--lines", "-n", help="显示行数")
):
    """查看日志文件内容"""
    # 尝试多个可能的路径
    possible_paths = [
        Path(__file__).parent.parent.parent / "logs",
        Path.cwd() / "logs",
        Path.home() / "alpha-new" / "logs",
    ]
    
    log_file = None
    for logs_dir in possible_paths:
        if logs_dir.exists():
            test_file = logs_dir / file_name
            if test_file.exists():
                log_file = test_file
                break
    
    if not log_file:
        console.print(f"[red]日志文件 {file_name} 不存在[/red]")
        return
    
    console.print(Panel(f"查看日志文件: {file_name}", title="日志查看"))
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.readlines()
        
        # 显示最后N行
        if len(content) > lines:
            content = content[-lines:]
            console.print(f"[yellow]显示最后 {lines} 行:[/yellow]")
        
        for line in content:
            console.print(line.rstrip())
            
    except Exception as e:
        console.print(f"[red]读取日志文件失败: {e}[/red]")

@app.command()
def clean(
    days: int = typer.Option(7, "--days", "-d", help="保留天数"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="确认删除")
):
    """清理旧日志文件"""
    import time
    
    logs_dir = Path(__file__).parent.parent.parent / "logs"
    if not logs_dir.exists():
        console.print("[yellow]日志目录不存在[/yellow]")
        return
    
    cutoff_time = time.time() - (days * 24 * 60 * 60)
    old_files = []
    
    for log_file in logs_dir.glob("*"):
        if log_file.is_file() and log_file.stat().st_mtime < cutoff_time:
            old_files.append(log_file)
    
    if not old_files:
        console.print("[green]没有需要清理的旧日志文件[/green]")
        return
    
    console.print(f"[yellow]找到 {len(old_files)} 个旧日志文件:[/yellow]")
    for log_file in old_files:
        mtime = datetime.fromtimestamp(log_file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        console.print(f"  {log_file.name} ({mtime})")
    
    if not confirm:
        confirm = Prompt.ask("确认删除这些文件?", choices=["y", "n"], default="n") == "y"
    
    if confirm:
        deleted_count = 0
        for log_file in old_files:
            try:
                log_file.unlink()
                deleted_count += 1
                console.print(f"[green]已删除: {log_file.name}[/green]")
            except Exception as e:
                console.print(f"[red]删除失败 {log_file.name}: {e}[/red]")
        
        console.print(Panel(f"[green]成功删除 {deleted_count} 个日志文件[/green]", title="清理完成"))
    else:
        console.print("[yellow]取消删除操作[/yellow]")

@app.command()
def level(
    module: str = typer.Argument(..., help="模块名称，如 alpha_new.api"),
    level: str = typer.Argument(..., help="日志级别: DEBUG, INFO, WARNING, ERROR, CRITICAL")
):
    """设置模块日志级别"""
    import logging
    
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if level.upper() not in valid_levels:
        console.print(f"[red]无效的日志级别: {level}[/red]")
        console.print(f"有效级别: {', '.join(valid_levels)}")
        return
    
    logger = logging.getLogger(module)
    logger.setLevel(getattr(logging, level.upper()))
    
    console.print(Panel(f"[green]模块 {module} 日志级别已设置为 {level.upper()}[/green]", title="日志级别设置"))

@app.command()
def interactive():
    """交互式日志管理"""
    while True:
        console.print("\n" + "="*50)
        console.print(Panel("日志管理工具", title="主菜单"))
        console.print("1. 查看日志文件列表")
        console.print("2. 查看日志文件内容")
        console.print("3. 清理旧日志文件")
        console.print("4. 设置日志级别")
        console.print("0. 退出")
        
        choice = Prompt.ask("请选择功能", choices=["1", "2", "3", "4", "0"], default="0")
        
        if choice == "1":
            show_log_files()
        elif choice == "2":
            log_files = get_log_files()
            if log_files:
                file_names = [f.name for f in log_files]
                file_name = Prompt.ask("请选择日志文件", choices=file_names)
                lines = Prompt.ask("显示行数", default="50")
                try:
                    view(file_name, int(lines))
                except Exception as e:
                    console.print(f"[red]查看失败: {e}[/red]")
        elif choice == "3":
            days = Prompt.ask("保留天数", default="7")
            try:
                clean(int(days))
            except Exception as e:
                console.print(f"[red]清理失败: {e}[/red]")
        elif choice == "4":
            module = Prompt.ask("模块名称", default="alpha_new.api")
            level = Prompt.ask("日志级别", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], default="INFO")
            try:
                # 调用level函数设置日志级别
                import logging
                logger = logging.getLogger(module)
                logger.setLevel(getattr(logging, level.upper()))
                console.print(Panel(f"[green]模块 {module} 日志级别已设置为 {level.upper()}[/green]", title="日志级别设置"))
            except Exception as e:
                console.print(f"[red]设置失败: {e}[/red]")
        elif choice == "0":
            console.print("[cyan]退出日志管理工具[/cyan]")
            break

if __name__ == "__main__":
    app() 