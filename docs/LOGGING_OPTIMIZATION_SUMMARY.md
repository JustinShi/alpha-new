# Alpha New 日志系统优化总结

## 优化概述

本次优化为 `src/alpha_new` 项目实现了完整的全局日志与模块日志显示分级系统，提供了专业的日志管理功能。

## 主要改进

### 1. 全局日志配置系统

**文件**: `src/alpha_new/__init__.py`

- ✅ 实现了统一的日志配置函数 `setup_logging()`
- ✅ 支持环境变量配置 (`LOG_LEVEL`, `LOG_FILE`)
- ✅ 支持配置文件配置 (`config/logging_config.toml`)
- ✅ 自动创建 `logs/` 目录
- ✅ 支持控制台和文件双重输出
- ✅ 统一的日志格式：`时间 | 模块名 | 级别 | 消息`

### 2. 模块级别日志记录器

**文件**: `src/alpha_new/utils/logger.py`

- ✅ 提供了模块级别的日志记录器获取函数
- ✅ 预定义了各模块的日志记录器：
  - `alpha_new.api`: API 请求和响应日志
  - `alpha_new.db`: 数据库操作日志
  - `alpha_new.scripts`: 脚本执行日志
  - `alpha_new.cli`: CLI 工具日志
  - `alpha_new.claim`: 空投领取日志

### 3. 配置文件支持

**文件**: `config/logging_config.toml`

- ✅ 支持全局日志级别配置
- ✅ 支持模块级别日志级别配置
- ✅ 支持第三方库日志级别控制
- ✅ 支持日志文件配置

### 4. 日志管理工具

**文件**: `src/alpha_new/scripts/log_manager.py`

- ✅ 命令行日志管理工具
- ✅ 日志文件列表查看
- ✅ 日志文件内容查看
- ✅ 旧日志文件清理
- ✅ 模块日志级别动态设置
- ✅ 交互式日志管理界面

### 5. 模块日志集成

已将所有模块的 `print` 语句替换为相应的日志级别：

#### API 模块 (`src/alpha_new/api/alpha_api.py`)
- ✅ 使用 `get_api_logger()` 获取日志记录器
- ✅ API 请求和响应日志记录

#### 数据库模块 (`src/alpha_new/db/ops.py`)
- ✅ 使用 `get_db_logger()` 获取日志记录器
- ✅ 数据库操作日志记录
- ✅ 用户查询和更新日志

#### 脚本模块
- ✅ `update_user_info.py`: 用户信息更新日志
- ✅ `query_airdrop_list.py`: 空投列表查询日志
- ✅ `auto_claim_airdrop.py`: 空投领取日志

#### CLI 模块 (`src/alpha_new/cli.py`)
- ✅ 使用 `get_cli_logger()` 获取日志记录器

## 日志级别说明

### 级别定义
- **DEBUG**: 详细的调试信息，用于开发调试
- **INFO**: 一般信息，记录程序运行状态
- **WARNING**: 警告信息，不影响程序运行但需要注意
- **ERROR**: 错误信息，程序运行出现问题
- **CRITICAL**: 严重错误，程序可能无法继续运行

### 默认配置
- 全局级别: INFO
- API 模块: INFO
- 数据库模块: DEBUG
- 脚本模块: INFO
- CLI 模块: INFO
- 领取模块: INFO
- 第三方库: WARNING

## 使用方法

### 1. 基本使用

```python
from alpha_new.utils import get_api_logger

logger = get_api_logger()
logger.info("这是一条信息日志")
logger.error("这是一条错误日志")
```

### 2. 环境变量配置

```bash
export LOG_LEVEL=DEBUG
export LOG_FILE=my_app.log
```

### 3. 配置文件配置

编辑 `config/logging_config.toml`:
```toml
[global]
level = "INFO"
file = "alpha_new.log"

[modules]
alpha_new.api = "DEBUG"
alpha_new.db = "INFO"
```

### 4. 日志管理工具

```bash
# 查看日志文件列表
poetry run python -m alpha_new.scripts.log_manager list

# 查看日志文件内容
poetry run python -m alpha_new.scripts.log_manager view alpha_new.log --lines 50

# 清理旧日志文件
poetry run python -m alpha_new.scripts.log_manager clean --days 7

# 设置模块日志级别
poetry run python -m alpha_new.scripts.log_manager level alpha_new.api DEBUG

# 交互式管理
poetry run python -m alpha_new.scripts.log_manager interactive
```

## 测试验证

### 测试脚本
- ✅ `test_logging.py`: 基本日志功能测试
- ✅ `test_logging_advanced.py`: 高级日志功能测试

### 测试结果
- ✅ 日志文件正确创建在 `logs/` 目录
- ✅ 不同级别的日志正确输出
- ✅ 模块级别的日志配置生效
- ✅ 日志管理工具功能正常
- ✅ 配置文件读取正常

## 文件结构

```
src/alpha_new/
├── __init__.py              # 全局日志配置
├── utils/
│   ├── __init__.py          # 工具模块导出
│   └── logger.py            # 日志工具函数
├── api/
│   └── alpha_api.py         # API日志集成
├── db/
│   └── ops.py               # 数据库日志集成
├── scripts/
│   ├── update_user_info.py  # 用户更新日志
│   ├── query_airdrop_list.py # 空投查询日志
│   ├── auto_claim_airdrop.py # 领取日志
│   └── log_manager.py       # 日志管理工具
└── cli.py                   # CLI日志集成

config/
└── logging_config.toml      # 日志配置文件

logs/
├── alpha_new.log            # 主日志文件
└── test_debug.log           # 测试日志文件

docs/
├── LOGGING_GUIDE.md         # 日志使用指南
└── LOGGING_OPTIMIZATION_SUMMARY.md # 优化总结
```

## 性能优化

### 1. 日志级别控制
- 生产环境使用 INFO 级别，减少 I/O 开销
- 开发环境使用 DEBUG 级别，获取详细信息
- 第三方库日志级别设置为 WARNING，减少噪音

### 2. 文件管理
- 自动创建日志目录
- 支持日志文件清理
- 支持多路径查找

### 3. 配置灵活性
- 环境变量优先级最高
- 配置文件次之
- 默认配置兜底

## 最佳实践

### 1. 日志级别选择
- 开发调试：使用 DEBUG 级别
- 生产运行：使用 INFO 级别
- 问题排查：临时设置为 DEBUG 级别

### 2. 日志内容
- 记录关键操作和状态变化
- 记录错误信息和异常堆栈
- 避免记录敏感信息

### 3. 日志管理
- 定期清理旧日志文件
- 监控日志文件大小
- 备份重要日志文件

## 总结

本次日志系统优化实现了：

1. **完整的日志分级系统** - 支持全局和模块级别的日志控制
2. **灵活的配置方式** - 支持环境变量、配置文件和代码配置
3. **专业的日志管理工具** - 提供完整的日志查看和管理功能
4. **良好的集成性** - 所有模块都已集成日志系统
5. **优秀的可维护性** - 统一的日志格式和管理方式

系统现在具备了企业级的日志管理能力，可以满足开发、测试和生产环境的各种需求。 