import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Optional
import argparse

from src.alpha_new.models.user_model import UserBaseDetailModel
from src.alpha_new.services.airdrop_service import (
    batch_claim_airdrops,
    batch_query_airdrops,
)
from src.alpha_new.services.trade_service import batch_place_orders
from src.alpha_new.utils.logging_config import setup_logging

def parse_arguments() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="Alpha新交易系统 - 多用户自动化交易和空投工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python -m src.alpha_new.main                    # 使用默认配置
  python -m src.alpha_new.main --users-type pc    # 仅使用PC端用户
  python -m src.alpha_new.main --log-level DEBUG  # 开启调试模式
  python -m src.alpha_new.main --config custom.toml  # 指定配置文件
        """
    )
    
    parser.add_argument(
        "--config",
        type=str,
        help="指定配置文件路径（支持TOML/YAML格式）"
    )
    
    parser.add_argument(
        "--users-type",
        choices=["pc", "mobile", "all"],
        default="all",
        help="指定用户类型 (默认: all)"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="设置日志级别 (默认: INFO)"
    )
    
    parser.add_argument(
        "--mode",
        choices=["airdrop", "trade", "all"],
        default="all",
        help="运行模式 (默认: all)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="模拟运行，不执行实际操作"
    )
    
    parser.add_argument(
        "--config-dir",
        type=str,
        default="config",
        help="配置文件目录 (默认: config)"
    )
    
    return parser.parse_args()


def load_users(config_dir: Path, users_type: str = "all") -> list:
    """加载用户配置"""
    users = []
    
    # 确定要加载的文件列表
    if users_type == "pc":
        filenames = ["pc_users.json"]
    elif users_type == "mobile":
        filenames = ["mobile_users.json"]
    else:  # all
        filenames = ["pc_users.json", "mobile_users.json"]
    
    for filename in filenames:
        path = config_dir / filename
        if path.exists():
            with path.open(encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    if isinstance(data, list):
                        for user_data in data:
                            try:
                                validated_user = UserBaseDetailModel(**user_data)
                                users.append(user_data)
                                logging.info(f"加载用户配置: {user_data.get('username', 'unknown')}")
                            except Exception as e:
                                logging.error(f"用户数据验证失败: {user_data} - {e}")
                except Exception as e:
                    logging.error(f"加载 {filename} 失败: {e}")
        else:
            logging.warning(f"配置文件不存在: {path}")
    
    return users


async def run_airdrop_mode(users: list, dry_run: bool = False) -> None:
    """运行空投模式"""
    logging.info("🎁 开始空投查询和领取...")
    
    if dry_run:
        logging.info("🔍 模拟模式: 仅查询，不执行实际领取")
        await batch_query_airdrops(users)
    else:
        await batch_query_airdrops(users)
        await batch_claim_airdrops(users, config_id="your_airdrop_config_id")
    
    logging.info("✅ 空投模式完成")


async def run_trade_mode(users: list, dry_run: bool = False) -> None:
    """运行交易模式"""
    logging.info("💱 开始交易操作...")
    
    order_payload = {
        "baseAsset": "ALPHA_118",
        "quoteAsset": "USDT",
        "side": "SELL",
        "price": 0.1,
        "quantity": 10,
    }
    
    if dry_run:
        logging.info(f"🔍 模拟模式: 准备下单 {order_payload}")
        logging.info("🔍 模拟模式: 不执行实际交易")
    else:
        await batch_place_orders(users, order_payload)
    
    logging.info("✅ 交易模式完成")


async def main() -> int:
    """主函数"""
    # 解析命令行参数
    args = parse_arguments()
    
    # 设置日志级别
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # 初始化日志
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # 打印启动信息
    logger.info("🚀 Alpha新交易系统启动")
    logger.info(f"📁 配置目录: {args.config_dir}")
    logger.info(f"👥 用户类型: {args.users_type}")
    logger.info(f"🎯 运行模式: {args.mode}")
    logger.info(f"🔍 模拟运行: {'是' if args.dry_run else '否'}")
    
    # 构建配置目录路径
    config_dir = Path(__file__).parent.parent / args.config_dir
    
    # 加载用户配置
    users = load_users(config_dir, args.users_type)
    
    if not users:
        logger.error(
            f"❌ 未加载到任何用户配置，请检查 {config_dir} 目录中的配置文件！"
        )
        logger.info("💡 提示: 可以从模板文件复制并修改配置")
        logger.info("   cp config/*_template.* config/")
        return 1
    
    logger.info(f"✅ 成功加载 {len(users)} 个用户配置")
    
    try:
        # 根据模式执行不同的操作
        if args.mode == "airdrop":
            await run_airdrop_mode(users, args.dry_run)
        elif args.mode == "trade":
            await run_trade_mode(users, args.dry_run)
        else:  # all
            await run_airdrop_mode(users, args.dry_run)
            await run_trade_mode(users, args.dry_run)
        
        logger.info("🎉 所有操作完成")
        return 0
        
    except KeyboardInterrupt:
        logger.info("⏹️  用户中断操作")
        return 130
    except Exception as e:
        logger.error(f"❌ 执行过程中发生错误: {e}")
        if args.log_level == "DEBUG":
            import traceback
            logger.debug(traceback.format_exc())
        return 1


def cli() -> None:
    """CLI入口点"""
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except Exception as e:
        logging.error(f"程序异常退出: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()
