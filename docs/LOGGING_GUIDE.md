# Alpha New 日志系统使用指南

## 概述

Alpha New 项目采用分级日志系统，支持全局日志配置和模块级别日志控制，提供完整的日志记录、查看和管理功能。

## 日志级别

- **DEBUG**: 详细的调试信息，用于开发调试
- **INFO**: 一般信息，记录程序运行状态
- **WARNING**: 警告信息，不影响程序运行但需要注意
- **ERROR**: 错误信息，程序运行出现问题
- **CRITICAL**: 严重错误，程序可能无法继续运行

## 模块日志记录器

项目为不同模块提供了专门的日志记录器：

- `alpha_new.api`: API 请求和响应日志
- `alpha_new.db`: 数据库操作日志
- `alpha_new.scripts`: 脚本执行日志
- `alpha_new.cli`: CLI 工具日志
- `alpha_new.claim`: 空投领取日志

## 配置方式

### 1. 环境变量配置

```bash
# 设置全局日志级别
export LOG_LEVEL=DEBUG

# 设置日志文件
export LOG_FILE=my_app.log
```

### 2. 配置文件配置

编辑 `config/logging_config.toml`:

```toml
[global]
level = "INFO"
file = "alpha_new.log"
console = true

[modules]
alpha_new.api = "INFO"
alpha_new.db = "DEBUG"
alpha_new.scripts = "INFO"
alpha_new.cli = "INFO"
alpha_new.claim = "INFO"

# 第三方库日志级别
httpx = "WARNING"
asyncio = "WARNING"
sqlalchemy = "WARNING"
```

### 3. 代码中动态设置

```python
from alpha_new.utils import get_logger

# 获取模块日志记录器
logger = get_logger("alpha_new.api", level="DEBUG")

# 或者使用预定义的日志记录器
from alpha_new.utils import get_api_logger
logger = get_api_logger()
```

## 日志管理工具

### 命令行使用

```bash
# 查看日志文件列表
poetry run python -m alpha_new.scripts.log_manager list

# 查看日志文件内容
poetry run python -m alpha_new.scripts.log_manager view alpha_new.log --lines 100

# 清理旧日志文件（保留7天）
poetry run python -m alpha_new.scripts.log_manager clean --days 7

# 设置模块日志级别
poetry run python -m alpha_new.scripts.log_manager level alpha_new.api DEBUG

# 交互式日志管理
poetry run python -m alpha_new.scripts.log_manager interactive
```

### 在代码中使用

```python
from alpha_new.scripts.log_manager import show_log_files, clean

# 显示日志文件列表
show_log_files()

# 清理旧日志文件
clean(days=7, confirm=True)
```

## 日志格式

日志输出格式：
```
2024-01-01 12:00:00 | alpha_new.api | INFO | POST https://www.binance.com/bapi/accounts/v1/private/account/user/base-detail
```

包含以下信息：
- 时间戳
- 模块名称
- 日志级别
- 日志消息

## 日志文件位置

日志文件默认保存在项目根目录的 `logs/` 文件夹中：
- `alpha_new.log`: 主日志文件
- `order_data.log`: 交易订单数据日志
- `claim_log_日期.log`: 空投领取结果汇总日志（按日期）
- `last_user_query_time.log`: 用户查询时间记录
- 其他自定义日志文件

空投领取日志格式说明：
```json
[
  {
    "timestamp": "2025-07-21 15:00:03",  // 领取时间
    "user_id": 1,                        // 用户ID
    "result": "[用户1] 领取成功",         // 领取结果
    "script": "semi_auto_claim_airdrop"  // 执行脚本
  },
  // 更多记录...
]
```

## 网络延迟优化

### 延迟问题诊断
如果发现定时执行但响应延迟的问题，可以：

1. **运行网络延迟测试**:
   ```bash
   poetry run python -m alpha_new.scripts.network_latency_test
   ```

2. **调整提前补偿时间**:
   在 `config/airdrop_config.toml` 中修改 `advance_ms` 参数：
   ```toml
   # 建议设置为网络延迟的1.5-2倍
   advance_ms = 3000  # 3秒提前补偿
   ```

3. **查看API请求延迟日志**:
   在主日志文件中查找 "API请求延迟" 关键词

## API日志用户追踪

### 用户ID标识
所有API调用日志现在都包含用户ID信息，便于问题排查：

```
# 带用户ID的日志格式
2025-07-21 17:57:56 | alpha_new.api | INFO | [用户1] POST https://www.binance.com/bapi/defi/v1/private/wallet-direct/buw/growth/claim-alpha-airdrop | config_id=xxx
2025-07-21 17:57:58 | alpha_new.api | INFO | [用户1] Response 200: {"code":"000000","message":null,...}

# 不带用户ID的日志格式（旧版本或未指定用户ID的调用）
2025-07-21 17:57:56 | alpha_new.api | INFO | POST https://www.binance.com/bapi/defi/v1/private/wallet-direct/buw/growth/claim-alpha-airdrop | config_id=xxx
2025-07-21 17:57:58 | alpha_new.api | INFO | Response 200: {"code":"000000","message":null,...}
```

### 日志筛选技巧
1. **按用户筛选**: 搜索 `[用户1]` 查看特定用户的所有API调用
2. **按API类型筛选**: 搜索 `claim-alpha-airdrop` 查看所有空投领取请求
3. **按响应状态筛选**: 搜索 `Response 200` 或 `Response 429` 等

## 最佳实践

### 1. 选择合适的日志级别

- **开发阶段**: 使用 DEBUG 级别获取详细信息
- **生产环境**: 使用 INFO 或 WARNING 级别
- **问题排查**: 临时设置为 DEBUG 级别

### 2. 模块级别配置

根据需要对不同模块设置不同的日志级别：
- API 模块：INFO 级别记录请求响应
- 数据库模块：DEBUG 级别记录 SQL 操作
- 脚本模块：INFO 级别记录执行状态

### 3. 日志文件管理

- 定期清理旧日志文件
- 监控日志文件大小
- 备份重要日志文件

### 4. 性能考虑

- 避免在循环中记录大量 DEBUG 日志
- 使用适当的日志级别减少 I/O 开销
- 考虑日志文件轮转机制

## 故障排除

### 1. 日志不输出

检查以下配置：
- 日志级别设置是否正确
- 日志文件路径是否有写权限
- 配置文件格式是否正确

### 2. 日志文件过大

- 降低日志级别
- 启用日志文件轮转
- 定期清理旧日志

### 3. 日志格式异常

- 检查日志格式化器配置
- 确认编码格式为 UTF-8
- 验证时间格式设置

## 示例

### 基本使用示例

```python
from alpha_new.utils import get_api_logger

logger = get_api_logger()

# 记录不同级别的日志
logger.debug("调试信息")
logger.info("一般信息")
logger.warning("警告信息")
logger.error("错误信息")
logger.critical("严重错误")
```

### 异常处理示例

```python
try:
    result = await api.get_user_info()
    logger.info(f"获取用户信息成功: {result}")
except Exception as e:
    logger.error(f"获取用户信息失败: {e}", exc_info=True)
```

### 性能监控示例

```python
import time
from alpha_new.utils import get_script_logger

logger = get_script_logger()

start_time = time.time()
# 执行操作
execution_time = time.time() - start_time
logger.info(f"操作执行完成，耗时: {execution_time:.2f}秒")
```
