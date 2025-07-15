"""
py缓存清理脚本
递归删除项目下所有 __pycache__ 目录和 *.pyc 文件。
"""
import logging
import shutil
from pathlib import Path

# 启用日志输出
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# 项目根目录（当前脚本的上一级目录）
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 遍历并处理
for path_obj in PROJECT_ROOT.rglob("*"):
    # 删除 __pycache__ 文件夹
    if path_obj.is_dir() and path_obj.name == "__pycache__":
        try:
            shutil.rmtree(path_obj)
            logger.info(f"已删除目录: {path_obj}")
        except Exception as e:
            logger.error(f"删除目录失败: {path_obj} - {e}")
    # 删除 .pyc 文件
    elif path_obj.is_file() and path_obj.suffix == ".pyc":
        try:
            path_obj.unlink()
            logger.info(f"已删除文件: {path_obj}")
        except Exception as e:
            logger.error(f"删除文件失败: {path_obj} - {e}")
