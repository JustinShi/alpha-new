"""
Alpha New Trading System
"""

import logging
import sys
from pathlib import Path

# 创建logs目录
logs_dir = Path(__file__).parent.parent.parent / "logs"
logs_dir.mkdir(exist_ok=True)

def setup_logging(level: str = "INFO", log_file: str | None = None, config_file: str | None = None) -> None:
    """设置全局日志配置"""
    import os
    import toml
    
    # 优先使用环境变量
    env_level = os.getenv("LOG_LEVEL")
    env_file = os.getenv("LOG_FILE")
    
    # 读取配置文件
    if config_file and Path(config_file).exists():
        try:
            config = toml.load(config_file)
            global_config = config.get("global", {})
            modules_config = config.get("modules", {})
            
            # 配置优先级：环境变量 > 配置文件 > 默认值
            level = env_level or global_config.get("level", level)
            log_file = env_file or global_config.get("file", log_file)
            
            # 应用模块级别的日志配置
            for module_name, module_level in modules_config.items():
                if isinstance(module_level, str):
                    logging.getLogger(module_name).setLevel(getattr(logging, module_level.upper(), logging.INFO))
                
        except Exception as e:
            print(f"读取日志配置文件失败: {e}")
    
    # 日志级别映射
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    
    log_level = level_map.get(level.upper(), logging.INFO)
    
    # 创建格式化器
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # 清除现有处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 文件处理器（如果指定）
    if log_file:
        file_path = logs_dir / log_file
        file_handler = logging.FileHandler(file_path, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # 设置特定模块的日志级别（如果配置文件中未指定）
    if not config_file or not Path(config_file).exists():
        logging.getLogger("httpx").setLevel(logging.WARNING)  # 减少HTTP请求日志
        logging.getLogger("asyncio").setLevel(logging.WARNING)  # 减少异步事件日志

# 默认设置
setup_logging(config_file="config/logging_config.toml")

__version__ = "1.0.0" 