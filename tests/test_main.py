"""
主函数CLI测试
"""
import pytest
import argparse
from unittest.mock import patch, MagicMock
from src.alpha_new.main import parse_arguments, load_users
from pathlib import Path
import tempfile
import json


class TestParseArguments:
    """命令行参数解析测试"""
    
    def test_default_arguments(self):
        """测试默认参数"""
        with patch('sys.argv', ['main.py']):
            args = parse_arguments()
            
            assert args.users_type == "all"
            assert args.log_level == "INFO"
            assert args.mode == "all"
            assert args.dry_run is False
            assert args.config_dir == "config"
    
    def test_custom_arguments(self):
        """测试自定义参数"""
        test_args = [
            'main.py',
            '--users-type', 'pc',
            '--log-level', 'DEBUG',
            '--mode', 'airdrop',
            '--dry-run',
            '--config-dir', 'custom_config'
        ]
        
        with patch('sys.argv', test_args):
            args = parse_arguments()
            
            assert args.users_type == "pc"
            assert args.log_level == "DEBUG"
            assert args.mode == "airdrop"
            assert args.dry_run is True
            assert args.config_dir == "custom_config"


class TestLoadUsers:
    """用户配置加载测试"""
    
    def test_load_pc_users(self):
        """测试加载PC用户配置"""
        # 创建临时配置文件
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            
            # 创建PC用户配置文件
            pc_users_data = [
                {
                    "username": "test_user_pc",
                    "device_type": "pc",
                    "headers": {"User-Agent": "test"},
                    "cookies": {"session": "test"}
                }
            ]
            
            pc_users_file = config_dir / "pc_users.json"
            with pc_users_file.open('w', encoding='utf-8') as f:
                json.dump(pc_users_data, f)
            
            # 测试加载PC用户
            users = load_users(config_dir, "pc")
            
            assert len(users) == 1
            assert users[0]["username"] == "test_user_pc"
    
    def test_load_mobile_users(self):
        """测试加载移动端用户配置"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            
            # 创建移动端用户配置文件
            mobile_users_data = [
                {
                    "username": "test_user_mobile",
                    "device_type": "mobile",
                    "headers": {"User-Agent": "mobile"}
                }
            ]
            
            mobile_users_file = config_dir / "mobile_users.json"
            with mobile_users_file.open('w', encoding='utf-8') as f:
                json.dump(mobile_users_data, f)
            
            # 测试加载移动端用户
            users = load_users(config_dir, "mobile")
            
            assert len(users) == 1
            assert users[0]["username"] == "test_user_mobile"
    
    def test_load_all_users(self):
        """测试加载所有用户配置"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            
            # 创建PC用户配置文件
            pc_users_data = [
                {
                    "username": "test_user_pc",
                    "device_type": "pc",
                    "headers": {"User-Agent": "test"},
                    "cookies": {"session": "test"}
                }
            ]
            
            # 创建移动端用户配置文件
            mobile_users_data = [
                {
                    "username": "test_user_mobile",
                    "device_type": "mobile",
                    "headers": {"User-Agent": "mobile"}
                }
            ]
            
            pc_users_file = config_dir / "pc_users.json"
            mobile_users_file = config_dir / "mobile_users.json"
            
            with pc_users_file.open('w', encoding='utf-8') as f:
                json.dump(pc_users_data, f)
            
            with mobile_users_file.open('w', encoding='utf-8') as f:
                json.dump(mobile_users_data, f)
            
            # 测试加载所有用户
            users = load_users(config_dir, "all")
            
            assert len(users) == 2
            usernames = [user["username"] for user in users]
            assert "test_user_pc" in usernames
            assert "test_user_mobile" in usernames
    
    def test_load_users_empty_directory(self):
        """测试空配置目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            
            users = load_users(config_dir, "all")
            
            assert len(users) == 0
    
    def test_load_users_invalid_json(self):
        """测试无效JSON配置"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            
            # 创建无效JSON文件
            pc_users_file = config_dir / "pc_users.json"
            with pc_users_file.open('w', encoding='utf-8') as f:
                f.write("invalid json content")
            
            # 应该返回空列表，不抛出异常
            users = load_users(config_dir, "pc")
            
            assert len(users) == 0 