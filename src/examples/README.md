# Alpha代币交易示例

本目录包含使用Alpha代币模块进行交易的完整示例，展示如何通过token symbol获取alpha_id并执行市价单交易。

## 📁 文件结构

```
src/examples/
├── README.md                    # 本说明文档
├── quick_start_trading.py       # 快速开始示例（推荐新手）
├── alpha_trading_example.py     # 完整功能示例（高级用户）
├── alpha_token_example.py       # Alpha代币示例
├── trading_config_example.json  # 配置文件示例
└── __init__.py                  # 包初始化文件
```

## 🚀 快速开始

### 1. 运行快速示例

```bash
# 进入项目根目录
cd alpha-new

# 运行快速示例（推荐方式）
python src/examples/quick_start_trading.py

# 或者作为模块运行
python -m src.examples.quick_start_trading
```

该示例提供交互式菜单，包含：
- 快速交易演示
- 列出所有可用代币
- 搜索特定代币

### 2. 基本使用流程

```python
import asyncio
import aiohttp
from src.alpha_new.api_clients.alpha_token_client import AlphaTokenClient
from src.alpha_new.api_clients.mkt_order_client import MarketOrderClient, OrderSide

async def basic_example():
    headers = {"Accept": "application/json", "User-Agent": "..."}
    
    async with aiohttp.ClientSession() as session:
        # 1. 初始化客户端
        token_client = AlphaTokenClient(session=session, headers=headers)
        order_client = MarketOrderClient(session=session, headers=headers)
        
        # 2. 查找代币获取alpha_id
        token_info = await token_client.get_token_by_symbol("ALPHA")
        alpha_id = token_info.alpha_id
        
        # 3. 构造交易对
        symbol = f"ALPHA_{alpha_id}USDT"
        
        # 4. 获取市价报价
        quote = await order_client.get_market_quote(symbol, OrderSide.BUY, 10.0)
        
        # 5. 执行交易（谨慎操作）
        # order = await order_client.place_market_order(symbol, OrderSide.BUY, 10.0)

asyncio.run(basic_example())
```

## 📋 详细示例说明

### 快速示例 (quick_start_trading.py)

**特点：**
- 🎯 交互式菜单
- 📋 代币列表查看
- 🔍 代币搜索功能
- ⚠️ 安全的模拟交易（默认不执行真实交易）

**适用场景：**
- 初学者了解功能
- 快速测试API连接
- 查看可用代币信息

### 交易演示示例 (alpha_trading_example.py)

**特点：**
- 🎯 简洁快速的演示风格
- 📋 分模块功能演示
- 🔍 代币查找演示
- 💰 市价报价演示
- 📝 下单流程演示

**适用场景：**
- 学习各个功能模块
- 了解完整交易流程
- 快速验证功能

## ⚙️ 配置说明

### 基本配置

```python
headers = {
    "Accept": "application/json",
    "Content-Type": "application/json", 
    "User-Agent": "Mozilla/5.0 (...)",
    "Referer": "https://www.binance.com/",
    "Origin": "https://www.binance.com"
}

# 如果需要认证
cookies = {
    "session_id": "your_session_id",
    # 其他必要的cookies
}
```

### 配置文件

参考 `trading_config_example.json` 文件，包含：
- 用户配置（headers, cookies）
- 交易参数（最大数量、金额限制等）
- API端点配置
- 通用设置（超时、重试等）

## 🔑 核心API使用

### 1. 获取代币信息

```python
# 根据符号查找代币
token_info = await token_client.get_token_by_symbol("ALPHA")

# 批量查找
symbols = ["ALPHA", "BTC", "ETH"] 
token_infos = {}
for symbol in symbols:
    info = await token_client.get_token_by_symbol(symbol)
    if info:
        token_infos[symbol] = info

# 获取所有代币
token_list = await token_client.get_token_list()
```

### 2. 构造交易对

```python
# Alpha代币的交易对格式：ALPHA_{alpha_id}USDT
alpha_id = token_info.alpha_id
trading_pair = f"ALPHA_{alpha_id}USDT"
```

### 3. 市价报价

```python
quote_result = await order_client.get_market_quote(
    symbol=trading_pair,
    side=OrderSide.BUY,  # 或 OrderSide.SELL
    quantity=10.0
)

if quote_result.success:
    data = quote_result.data
    price = data.get('price')      # 预估价格
    amount = data.get('amount')    # 预估金额
    fee = data.get('fee')          # 预估手续费
```

### 4. 下市价单

```python
order_result = await order_client.place_market_order(
    symbol=trading_pair,
    side=OrderSide.BUY,
    quantity=10.0
)

if order_result.success:
    order_data = order_result.data
    order_id = order_data.get('orderId')
    status = order_data.get('status')
```

## ⚠️ 安全提醒

### 🛡️ 交易安全
1. **测试环境优先**：先在测试环境验证代码
2. **小额测试**：使用小额资金测试交易流程
3. **配置验证**：确保headers和cookies正确配置
4. **错误处理**：始终检查API返回结果

### 🔐 配置安全
1. **敏感信息**：不要将真实cookies提交到代码仓库
2. **权限控制**：使用最小权限原则配置API访问
3. **定期轮换**：定期更新session cookies
4. **环境隔离**：开发和生产环境分离

### 📊 监控建议
1. **日志记录**：记录所有交易操作
2. **统计监控**：跟踪成功率和响应时间
3. **异常告警**：设置关键错误告警
4. **资金监控**：实时监控账户余额变化

## 🚨 重要提醒

### ⚠️ 风险声明
- 本示例仅供学习和测试使用
- 实际交易请谨慎操作，自行承担风险
- 建议先在测试环境充分验证
- 交易前请确保充分理解市场风险

### 🔧 故障排除

**常见问题:**

1. **导入错误**
   ```bash
   # 确保在项目根目录运行
   cd alpha-new
   python src/examples/quick_start_trading.py
   
   # 或者使用模块方式运行
   python -m src.examples.quick_start_trading
   ```

2. **API请求失败**
   - 检查网络连接
   - 验证headers配置
   - 确认cookies有效性

3. **代币未找到**
   - 验证代币符号拼写
   - 检查代币是否在支持列表中
   - 尝试获取完整代币列表确认

4. **交易失败**
   - 检查账户权限
   - 验证交易对格式
   - 确认余额充足

## 📞 技术支持

如有问题，请参考：
1. 项目主README文档
2. API参考文档 (`docs/API_REFERENCE_MERGED.md`)
3. 代码注释和类型提示

---

**祝您交易顺利！** 🎉 