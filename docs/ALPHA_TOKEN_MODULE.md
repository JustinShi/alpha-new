# Alpha代币信息模块

## 概述

Alpha代币信息模块提供了完整的Alpha代币信息获取和管理功能，包括数据模型、API客户端和服务层。该模块基于W3W.Finance平台的Alpha代币信息API构建。

## 模块结构

```
src/
├── models/
│   └── alpha_token_model.py      # 数据模型
├── api_clients/
│   └── alpha_token_client.py     # API客户端
├── services/
│   └── alpha_token_service.py    # 服务层
└── examples/
    └── alpha_token_example.py    # 使用示例
```

## 主要功能

### 1. 数据模型 (`alpha_token_model.py`)

- **AlphaTokenInfo**: Alpha代币基本信息模型
- **AlphaTokenListResponse**: 代币列表响应模型
- **AlphaTokenFilter**: 代币过滤器

#### 字段说明

```python
class AlphaTokenInfo:
    alpha_id: str          # Alpha代币ID
    chain_id: str          # 链ID
    chain_name: str        # 链名称
    contract_address: str  # 合约地址
    symbol: str            # 代币符号
    token_id: str          # 代币ID
    total_supply: str      # 总供应量
```

### 2. API客户端 (`alpha_token_client.py`)

提供低级别的API访问功能：

#### 主要方法

- `get_token_list()`: 获取所有Alpha代币列表
- `get_token_by_symbol(symbol)`: 根据符号获取代币信息
- `get_tokens_by_chain(chain_id)`: 获取指定链上的代币
- `search_tokens(filter_obj)`: 根据过滤条件搜索代币

#### 特性

- ✅ 自动缓存（5分钟默认）
- ✅ 重试机制（指数退避）
- ✅ 错误处理
- ✅ 统计信息

### 3. 服务层 (`alpha_token_service.py`)

提供高级业务功能：

#### 主要方法

- `get_all_tokens()`: 获取所有代币信息
- `get_token_info(symbol)`: 获取指定代币信息
- `get_chain_summary()`: 获取各链摘要统计
- `get_popular_tokens()`: 获取热门代币（按供应量）
- `batch_get_tokens()`: 批量获取代币信息
- `search_tokens()`: 高级搜索功能

#### 高级特性

- ✅ 多级缓存（API + 本地索引）
- ✅ 代理池支持
- ✅ 并发处理
- ✅ 统计分析
- ✅ 全局服务实例

## 使用方法

### 基本用法

```python
import asyncio
import aiohttp
from src.api_clients.alpha_token_client import AlphaTokenClient

async def basic_example():
    async with aiohttp.ClientSession() as session:
        client = AlphaTokenClient(session=session)
        
        # 获取所有代币
        token_list = await client.get_token_list()
        print(f"获取到 {len(token_list)} 个代币")
        
        # 搜索特定代币
        token = await client.get_token_by_symbol("BR")
        if token:
            print(f"找到代币: {token.symbol} on {token.chain_name}")

asyncio.run(basic_example())
```

### 服务层用法

```python
import asyncio
import aiohttp
from src.services.alpha_token_service import AlphaTokenService

async def service_example():
    async with aiohttp.ClientSession() as session:
        service = AlphaTokenService(session=session)
        await service.initialize()
        
        # 获取链摘要
        chain_summary = await service.get_chain_summary()
        for chain_id, summary in chain_summary.items():
            print(f"链 {chain_id}: {summary['token_count']} 个代币")
        
        # 获取热门代币
        popular = await service.get_popular_tokens(limit=5)
        for token in popular:
            print(f"{token.symbol}: {token.total_supply}")

asyncio.run(service_example())
```

### 搜索和过滤

```python
from src.models.alpha_token_model import AlphaTokenFilter

# 创建过滤器
filter_obj = AlphaTokenFilter(
    chain_id="56",          # BSC链
    symbol_pattern="BR",    # 符号包含"BR"
    min_supply=1000000     # 最小供应量
)

# 搜索代币
results = await service.search_tokens(
    chain_id="56",
    symbol_pattern="BR",
    min_supply=1000000
)
```

## API端点

### 获取Alpha代币列表

- **URL**: `GET https://www.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/cex/alpha/all/token/list`
- **认证**: 无需认证（公开API）
- **缓存**: 支持客户端缓存

### 响应格式

```json
{
  "success": true,
  "code": "000000",
  "data": [
    {
      "alphaId": "string",
      "chainId": "string", 
      "chainName": "string",
      "contractAddress": "string",
      "symbol": "string",
      "tokenId": "string",
      "totalSupply": "string"
    }
  ]
}
```

## 性能优化

### 缓存策略

1. **API客户端缓存**: 5分钟默认缓存时间
2. **服务层本地索引**: 内存中的快速查找
3. **多级缓存**: API缓存 + 本地索引 + 统计缓存

### 性能特性

- ✅ 并发请求支持
- ✅ 批量操作优化
- ✅ 智能缓存失效
- ✅ 代理池负载均衡

## 错误处理

### 重试机制

- 指数退避重试（1s, 2s, 4s...）
- 可配置最大重试次数
- 区分临时错误和永久错误

### 错误类型

```python
# 网络错误
aiohttp.ClientError

# 响应格式错误  
ValueError

# 超时错误
asyncio.TimeoutError
```

## 配置选项

### 客户端配置

```python
client = AlphaTokenClient(
    session=session,           # aiohttp会话
    headers=headers,           # HTTP头部
    timeout=30.0,             # 超时时间（秒）
    max_retries=3,            # 最大重试次数
    retry_delay=1.0,          # 重试延迟（秒）
    cache_duration=300        # 缓存时间（秒）
)
```

### 服务层配置

```python
service = AlphaTokenService(
    session=session,          # aiohttp会话
    headers=headers,          # HTTP头部
    use_proxy=True,          # 是否使用代理
    cache_duration=300       # 缓存时间（秒）
)
```

## 统计信息

### 客户端统计

```python
stats = client.get_stats()
print(f"请求次数: {stats['requests_count']}")
print(f"缓存命中: {stats['cache_hits']}")
print(f"错误次数: {stats['errors_count']}")
```

### 服务层统计

```python
stats = service.get_service_stats()
print(f"总查询: {stats['service_stats']['total_queries']}")
print(f"唯一符号: {stats['service_stats']['unique_symbols_count']}")
print(f"缓存命中率: {stats['service_stats']['cache_hits']}")
```

## 运行示例

```bash
# 运行完整示例
python src/examples/alpha_token_example.py

# 测试API客户端
python -m src.api_clients.alpha_token_client

# 测试服务层
python -m src.services.alpha_token_service
```

## 注意事项

1. **API限制**: 公开API，但建议控制请求频率
2. **内存使用**: 服务层会缓存代币列表，注意内存使用
3. **代理设置**: 如使用代理，确保`config/proxies.txt`文件存在
4. **错误恢复**: 网络错误会自动重试，应用错误需手动处理

## 扩展功能

### 自定义过滤器

```python
class CustomFilter:
    def matches(self, token: AlphaTokenInfo) -> bool:
        # 自定义过滤逻辑
        return token.symbol.startswith("BTC")

# 使用自定义过滤器
custom_filter = CustomFilter()
filtered_tokens = [token for token in all_tokens.data if custom_filter.matches(token)]
```

### 自定义缓存策略

```python
# 禁用缓存
token_list = await client.get_token_list(use_cache=False)

# 强制刷新
token_list = await service.get_all_tokens(force_refresh=True)

# 清除所有缓存
await service.clear_all_cache()
```

## 技术依赖

- **aiohttp**: HTTP客户端
- **pydantic**: 数据验证和序列化
- **asyncio**: 异步编程
- **python 3.8+**: 最低Python版本要求

## 贡献指南

1. 遵循现有代码风格
2. 添加适当的类型注解
3. 编写单元测试
4. 更新文档
5. 确保向后兼容性 