import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path  # 导入 Path


def setup_logging(
    log_dir: str = "logs", log_file: str = "app.log", level: int = logging.INFO
) -> None:  # 添加类型提示
    """
    配置全局日志记录。
    日志将输出到控制台和文件。
    文件日志将进行轮转。
    """
    # 确保日志目录存在
    log_path = Path(log_dir)
    if not log_path.exists():
        log_path.mkdir(
            parents=True
        )  # 使用 Path.mkdir() 创建目录, parents=True 确保创建父目录

    log_filepath = log_path / log_file  # 使用 Path 对象构建路径

    # 创建一个logger
    logger = logging.getLogger()
    logger.setLevel(level)

    # 避免重复添加handler
    if not logger.handlers:
        # 创建一个handler, 用于写入日志文件(轮转)
        # 每个文件最大10MB, 保留5个备份文件
        file_handler = RotatingFileHandler(
            log_filepath, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setLevel(level)

        # 创建一个handler, 用于输出到控制台
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)

        # 定义handler的输出格式
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # 给logger添加handler
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    # 设置requests库的日志级别, 避免过多输出
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


if __name__ == "__main__":
    setup_logging()
    logging.info("这是一个信息日志。")
    logging.warning("这是一个警告日志。")
    logging.error("这是一个错误日志。")
