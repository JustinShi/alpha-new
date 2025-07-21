# API 日志用户追踪改进

## 📋 问题描述

在之前的日志系统中，API调用日志缺少用户ID信息，导致：

1. **无法追踪特定用户的API调用**
2. **问题排查困难** - 不知道哪个响应对应哪个用户
3. **监控效果差** - 无法分析单个用户的API使用情况

### 问题示例

```log
# 之前的日志格式 - 无法区分用户
2025-07-21 15:00:03 | alpha_new.api | INFO | Response 200: {"code":"000000","message":null,...}
2025-07-21 15:00:07 | alpha_new.api | INFO | Response 200: {"code":"160006","message":"insufficient inventory",...}
```

**问题**: 无法知道这两个响应分别对应哪个用户的请求。

## ✅ 解决方案

### 1. **AlphaAPI 类改进**

#### 添加用户ID参数
```python
class AlphaAPI:
    def __init__(self, headers: dict[str, str], cookies: dict[str, str] | None = None, user_id: int | None = None):
        self.headers = headers
        self.cookies = cookies
        self.user_id = user_id  # 新增用户ID用于日志追踪
```

#### 日志格式改进
```python
async def claim_airdrop(self, config_id: str) -> Any:
    user_prefix = f"[用户{self.user_id}] " if self.user_id else ""
    logger.info(f"{user_prefix}POST {url} | config_id={config_id}")
    # ... API调用 ...
    logger.info(f"{user_prefix}Response {resp.status_code}: {resp.text}")
```

### 2. **所有脚本更新**

更新了以下脚本中的 AlphaAPI 实例化：

- ✅ `auto_claim_airdrop.py`
- ✅ `skiplist_auto_claim_airdrop.py`
- ✅ `semi_auto_claim_airdrop.py`
- ✅ `auto_trader.py`
- ✅ `query_token_orders.py`
- ✅ `update_user_info.py`
- ✅ `query_airdrop_list.py`
- ✅ `get_order_history_stats.py`

### 3. **所有API方法覆盖**

为以下API方法添加了用户ID前缀：

- ✅ `claim_airdrop()` - 空投领取
- ✅ `query_airdrop_list()` - 空投列表查询
- ✅ `get_user_info()` - 用户信息获取
- ✅ `get_alpha_score()` - Alpha积分查询
- ✅ `get_wallet_balance()` - 钱包余额查询

## 📊 改进效果

### 新的日志格式

```log
# 现在的日志格式 - 清晰标识用户
2025-07-21 17:57:56 | alpha_new.api | INFO | [用户1] POST https://www.binance.com/bapi/defi/v1/private/wallet-direct/buw/growth/claim-alpha-airdrop | config_id=e64dba63c9f9462c9e4e2cd299ecec7e
2025-07-21 17:57:58 | alpha_new.api | INFO | [用户1] Response 200: {"code":"000000","message":null,"data":{"configId":"e64dba63c9f9462c9e4e2cd299ecec7e","claimStatus":null}}

2025-07-21 17:58:00 | alpha_new.api | INFO | [用户4] POST https://www.binance.com/bapi/defi/v1/private/wallet-direct/buw/growth/claim-alpha-airdrop | config_id=e64dba63c9f9462c9e4e2cd299ecec7e
2025-07-21 17:58:07 | alpha_new.api | INFO | [用户4] Response 200: {"code":"160006","message":"insufficient inventory"}
```

### 优势对比

| 特性 | 改进前 | 改进后 ✅ |
|------|--------|-----------|
| **用户追踪** | ❌ 无法识别用户 | ✅ 清晰标识用户ID |
| **问题排查** | ❌ 需要猜测对应关系 | ✅ 直接定位用户问题 |
| **日志筛选** | ❌ 只能按时间筛选 | ✅ 可按用户ID筛选 |
| **监控分析** | ❌ 无法分析单用户行为 | ✅ 支持用户级别分析 |
| **调试效率** | ❌ 低效 | ✅ 高效 |

## 🔍 使用方法

### 1. **日志筛选技巧**

#### 按用户筛选
```bash
# 查看用户1的所有API调用
grep "\[用户1\]" logs/alpha_new.log

# 查看用户4的空投领取记录
grep "\[用户4\].*claim-alpha-airdrop" logs/alpha_new.log
```

#### 按API类型筛选
```bash
# 查看所有空投领取请求
grep "claim-alpha-airdrop" logs/alpha_new.log

# 查看所有429错误
grep "Response 429" logs/alpha_new.log
```

#### 按响应状态筛选
```bash
# 查看所有成功响应
grep "Response 200" logs/alpha_new.log

# 查看所有错误响应
grep -E "Response [45][0-9][0-9]" logs/alpha_new.log
```

### 2. **问题排查流程**

#### 空投领取问题排查
1. **确定问题用户**: 从业务日志中找到失败的用户ID
2. **查看API调用**: `grep "[用户X]" logs/alpha_new.log`
3. **分析响应**: 查看对应的Response日志
4. **定位问题**: 根据错误码和消息确定问题原因

#### 网络延迟分析
1. **查看请求时间**: 找到POST请求的时间戳
2. **查看响应时间**: 找到对应Response的时间戳
3. **计算延迟**: 响应时间 - 请求时间
4. **优化配置**: 根据延迟调整advance_ms参数

### 3. **测试验证**

运行测试脚本验证功能：
```bash
poetry run python -m alpha_new.scripts.test_user_id_logging
```

## 🎯 最佳实践

### 1. **开发规范**
- 所有新的API调用都应该传入user_id参数
- 确保日志中包含足够的上下文信息
- 使用统一的日志格式

### 2. **监控建议**
- 定期检查日志中是否有未标识用户ID的API调用
- 监控特定用户的API调用频率和成功率
- 设置告警规则，及时发现异常

### 3. **故障排查**
- 优先查看用户级别的日志
- 结合业务日志和API日志进行分析
- 保留足够的日志历史用于问题回溯

## 🚀 后续改进计划

### 短期
1. **添加请求ID**: 为每个API请求生成唯一ID
2. **性能监控**: 记录每个API调用的耗时
3. **错误统计**: 按用户统计API错误率

### 长期
1. **结构化日志**: 使用JSON格式的结构化日志
2. **日志分析工具**: 开发专门的日志分析工具
3. **实时监控**: 集成到监控系统中

## 📝 总结

通过这次改进，我们成功解决了API日志中用户追踪的问题，大大提高了：

- ✅ **问题排查效率** - 可以快速定位特定用户的问题
- ✅ **监控能力** - 支持用户级别的API监控
- ✅ **调试体验** - 日志信息更加清晰和有用
- ✅ **运维质量** - 更好的故障定位和分析能力

这个改进为后续的系统优化和问题排查奠定了良好的基础。
