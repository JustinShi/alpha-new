# Alpha交易系统快速入门指南

## 🚀 5分钟快速上手

### 1. 环境准备

```bash
# 克隆项目
git clone <项目地址>
cd alpha-new

# 安装依赖
pip install -e .

# 检查安装
python -c "from src.alpha_new.models.alpha_token_model import AlphaTokenInfo; print('✅ 安装成功')"
```

### 2. 基础配置

#### 创建用户配置文件

```bash
# 复制模板文件
cp config/pc_users.json.template config/pc_users.json
cp config/mobile_users.json.template config/mobile_users.json
cp config/airdrop_config.yaml.template config/airdrop_config.yaml
```

#### 获取浏览器认证信息

1. **打开币安Alpha页面**: https://www.binance.com/zh-CN/alpha/
2. **F12打开开发者工具** → Network标签
3. **执行任意操作**（如查看代币）
4. **找到API请求**，右键 → Copy → Copy as cURL
5. **提取headers和cookies**到配置文件

#### 配置示例

```json
{
  "username": "我的账户",
  "device_type": "pc",
  "headers": {
    "User-Agent": "从浏览器复制",
    "Accept": "application/json",
    "...": "更多headers"
  },
  "cookies": {
    "从浏览器复制真实cookies": "重要：不要泄露"
  }
}
```

### 3. 快速测试

#### 测试Alpha代币查询

```bash
# 运行代币查询示例
cd src/examples
python alpha_token_example.py
```

#### 测试交易示例

```bash
# 运行交易示例（模拟模式）
python alpha_trading_example.py
```

#### 测试完整系统

```bash
# 模拟运行（安全测试）
python -m src.alpha_new.main --dry-run --log-level DEBUG

# 仅运行空投功能
python -m src.alpha_new.main --mode airdrop --dry-run

# 仅使用PC端用户
python -m src.alpha_new.main --users-type pc --dry-run
```

### 4. 主要功能

| 功能 | 命令 | 说明 |
|------|------|------|
| 🔍 代币查询 | `python src/examples/alpha_token_example.py` | 查找Alpha代币信息 |
| 💱 交易演示 | `python src/examples/alpha_trading_example.py` | 市价单交易演示 |
| 🎁 空投领取 | `python -m src.alpha_new.main --mode airdrop` | 自动领取空投 |
| 🤖 全自动 | `python -m src.alpha_new.main` | 完整自动化流程 |

### 5. 安全提醒

- ⚠️ **首次使用必须加 `--dry-run` 参数进行模拟测试**
- ⚠️ **确认配置正确后再去掉 `--dry-run` 进行真实操作**
- ⚠️ **配置文件包含敏感信息，切勿泄露或提交到代码仓库**
- ⚠️ **建议小额测试，确认无误后再大额使用**

## 📋 详细配置

### 用户配置 (config/pc_users.json)

```json
[
  {
    "username": "用户标识名",
    "device_type": "pc",
    "description": "配置说明",
    "headers": {
      "authority": "www.binance.com",
      "accept": "*/*",
      "accept-language": "zh-CN,zh;q=0.9",
      "content-type": "application/json",
      "user-agent": "完整的User-Agent字符串",
      "referer": "https://www.binance.com/zh-CN/alpha/",
      "origin": "https://www.binance.com"
    },
    "cookies": {
      "重要提醒": "这里放置从浏览器获取的真实cookies",
      "bnc-uuid": "设备标识",
      "lang": "zh-CN",
      "logined": "y",
      "其他cookies": "从浏览器开发者工具获取"
    },
    "config": {
      "max_retries": 3,
      "timeout": 30,
      "log_level": "INFO"
    }
  }
]
```

### 空投配置 (config/airdrop_config.yaml)

```yaml
global_config:
  enabled: true
  schedule:
    check_interval: 2  # 检查间隔（小时）
    daily_times: ["09:00", "15:00", "21:00"]
  
token_configs:
  BR:  # 代币符号
    enabled: true
    priority: 1
    custom_settings:
      min_claim_amount: 0.05
      max_daily_claims: 10

user_configs:
  用户标识名:
    enabled: true
    priority: 1
    reward_thresholds:
      min_claim_amount: 0.001
      max_daily_claims: 50
```

## 🛠️ 高级功能

### 代码质量检查

```bash
# 运行代码检查
python -m ruff check src/
python -m black --check src/
python -m mypy src/alpha_new/

# 自动修复格式问题
python -m ruff check src/ --fix
python -m black src/
```

### 运行测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行特定测试
python -m pytest tests/test_models.py -v

# 生成测试报告
python -m pytest tests/ --cov=src.alpha_new --cov-report=html
```

### 性能监控

```bash
# 启用详细日志
python -m src.alpha_new.main --log-level DEBUG

# 查看日志文件
tail -f logs/app.log
```

## ❓ 常见问题

### Q: 提示"未加载到任何用户配置"？
A: 检查配置文件是否存在且格式正确：
```bash
# 检查文件是否存在
ls -la config/
# 验证JSON格式
python -c "import json; print(json.load(open('config/pc_users.json')))"
```

### Q: 网络连接失败？
A: 检查网络和代理设置：
```bash
# 测试网络连接
curl -I https://www.binance.com
# 检查代理配置
cat config/proxies.txt
```

### Q: 认证失败？
A: 更新浏览器认证信息：
1. 重新获取headers和cookies
2. 确认User-Agent匹配
3. 检查session是否过期

### Q: 如何安全测试？
A: 始终先使用模拟模式：
```bash
# 模拟运行，不执行实际操作
python -m src.alpha_new.main --dry-run --log-level DEBUG
```

## 📞 获取帮助

1. **查看详细文档**: [docs/](docs/)
2. **API参考**: [docs/API_REFERENCE_MERGED.md](docs/API_REFERENCE_MERGED.md)
3. **架构分析**: [docs/PROJECT_ARCHITECTURE_ANALYSIS.md](docs/PROJECT_ARCHITECTURE_ANALYSIS.md)
4. **用户配置**: [docs/USER_CONFIG_GUIDE.md](docs/USER_CONFIG_GUIDE.md)

## 🔄 版本更新

```bash
# 更新代码
git pull origin main

# 更新依赖
pip install -e . --upgrade

# 运行测试确认
python -m pytest tests/ -v
```

---

**🎯 记住：先模拟测试，再真实操作！** 