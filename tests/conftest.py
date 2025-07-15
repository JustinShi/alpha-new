"""
pytest配置文件
"""
import pytest
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环用于异步测试"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_token_data():
    """示例代币数据"""
    return {
        "alphaId": "ALPHA_118",
        "chainId": "56",
        "chainName": "BSC",
        "contractAddress": "0xff7d6a96ae471bbcd7713af9cb1feeb16cf56b41",
        "symbol": "BR",
        "tokenId": "063898D505CAF5E575D14DC5D5022B2B",
        "totalSupply": "1000000000"
    }


@pytest.fixture
def sample_user_config():
    """示例用户配置"""
    return {
        "username": "test_user",
        "device_type": "pc",
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json"
        },
        "cookies": {
            "session_id": "test_session",
            "auth_token": "test_token"
        }
    } 