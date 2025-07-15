# 用户配置指南

本指南详细说明如何配置和使用Alpha交易系统的用户配置文件。

## 📋 配置文件概览

### 配置文件类型

```
config/
├── pc_users_template.json      # PC端用户配置模板
├── mobile_users_template.json  # 移动端用户配置模板
├── airdrop_config_template.yaml # 空投配置模板
├── config_template.toml        # 通用配置模板
└── proxies.txt                 # 代理服务器列表
```

### 实际配置文件

```
config/
├── pc_users.json              # PC端用户实际配置
├── mobile_users.json          # 移动端用户实际配置
├── airdrop_config.yaml        # 空投实际配置
└── app_config.toml            # 应用实际配置
```

## 🔧 配置步骤

### 1. 创建PC端用户配置

```bash
# 复制模板文件
cp config/pc_users_template.json config/pc_users.json
```

然后编辑 `config/pc_users.json`，填写真实的认证信息：

```json
{
  "username": "your_actual_username",
  "headers": {
    "User-Agent": "your_actual_user_agent",
    "// 从浏览器开发者工具获取": "..."
  },
  "cookies": {
    "session_id": "从浏览器获取的真实session_id",
    "auth_token": "从浏览器获取的真实auth_token",
    "// 更多cookies": "..."
  }
}
```

### 2. 创建移动端用户配置

```bash
# 复制模板文件
cp config/mobile_users_template.json config/mobile_users.json
```

移动端配置与PC端类似，但不需要cookies（仅headers）。

### 3. 创建空投配置

```bash
# 复制模板文件
cp config/airdrop_config_template.yaml config/airdrop_config.yaml
```

根据需要启用/禁用空投任务，设置奖励阈值等。

### 4. 创建应用配置

```bash
# 复制模板文件
cp config/config_template.toml config/app_config.toml
```

## 🔑 如何获取认证信息

### 从浏览器获取Headers和Cookies

1. **打开浏览器开发者工具**
   - Chrome: F12 或 Ctrl+Shift+I
   - Firefox: F12 或 Ctrl+Shift+I

2. **进入Network标签页**
   - 刷新页面或执行一个操作
   - 观察网络请求

3. **找到API请求**
   - 查找对应的API请求（如登录、交易等）
   - 右键点击请求 → Copy → Copy as cURL

4. **提取信息**
   - Headers: 从cURL命令中提取 `-H` 参数
   - Cookies: 从cURL命令中提取 `--cookie` 参数

### 示例：从cURL提取信息

```bash
curl 'https://www.binance.com/api/v1/account' \
  -H 'User-Agent: Mozilla/5.0...' \
  -H 'Accept: application/json' \
  --cookie 'session_id=abc123; auth_token=xyz789'
```

提取结果：
- User-Agent: `Mozilla/5.0...`
- Accept: `application/json`
- session_id: `abc123`
- auth_token: `xyz789`

## 📝 配置字段说明

### PC端用户配置字段

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| username | string | ✅ | 用户标识名 |
| device_type | string | ✅ | 设备类型（"pc"） |
| description | string | ❌ | 配置说明 |
| headers | object | ✅ | HTTP请求头 |
| cookies | object | ✅ | 会话cookies |
| config | object | ❌ | 个人配置选项 |

### 移动端用户配置字段

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| username | string | ✅ | 用户标识名 |
| device_type | string | ✅ | 设备类型（"mobile"） |
| headers | object | ✅ | HTTP请求头 |
| config | object | ❌ | 个人配置选项 |

### 重要Headers说明

```json
{
  "User-Agent": "浏览器标识，必须与实际浏览器匹配",
  "Accept": "接受的内容类型",
  "Accept-Language": "语言偏好",
  "Referer": "来源页面URL",
  "Origin": "请求来源域名",
  "Content-Type": "请求内容类型",
  "X-Requested-With": "Ajax请求标识"
}
```

### 重要Cookies说明

```json
{
  "session_id": "会话ID，用于身份验证",
  "auth_token": "认证令牌，用于API访问",
  "user_id": "用户ID标识",
  "csrf_token": "CSRF保护令牌",
  "device_id": "设备标识符"
}
```

## ⚠️ 安全注意事项

### 1. 敏感信息保护

- ❌ **绝对不要**将真实的配置文件提交到Git仓库
- ✅ 使用 `.gitignore` 忽略配置文件
- ✅ 定期更换认证token
- ✅ 使用环境变量存储敏感信息

### 2. .gitignore 配置

```gitignore
# 用户配置文件
config/pc_users.json
config/mobile_users.json
config/airdrop_config.yaml
config/app_config.toml

# 敏感数据
data/
logs/
*.db
*.log
```

### 3. 配置验证

系统会在启动时验证配置：
- ✅ 必需字段检查
- ✅ 格式验证
- ✅ 连通性测试

## 🚀 使用示例

### 命令行使用

```bash
# 使用默认配置启动
python src/alpha_new/main.py

# 指定配置文件
python src/alpha_new/main.py --config config/custom_config.toml

# 仅使用PC端用户
python src/alpha_new/main.py --users-type pc

# 启用调试模式
python src/alpha_new/main.py --log-level DEBUG
```

### 代码中使用

```python
from src.alpha_new.main import main
import asyncio

# 程序化执行
async def run_trading():
    await main()

if __name__ == "__main__":
    asyncio.run(run_trading())
```

## 🔧 高级配置

### 代理配置

在 `config/proxies.txt` 中添加代理：

```
http://proxy1.example.com:8080
socks5://proxy2.example.com:1080
http://username:password@proxy3.example.com:3128
```

### 日志配置

```python
# 在配置中设置日志级别
"config": {
  "log_level": "DEBUG",  # DEBUG, INFO, WARNING, ERROR
  "enable_logging": true,
  "log_file": "logs/user1.log"
}
```

### 重试配置

```python
"config": {
  "max_retries": 3,      # 最大重试次数
  "timeout": 30,         # 请求超时时间
  "retry_delay": 2       # 重试间隔
}
```

## 🐛 故障排除

### 常见问题

1. **认证失败**
   - 检查cookies是否过期
   - 验证User-Agent是否正确
   - 确认headers完整性

2. **连接超时**
   - 检查网络连接
   - 验证代理配置
   - 调整timeout设置

3. **配置格式错误**
   - 验证JSON格式
   - 检查字段名拼写
   - 确认数据类型正确

### 调试技巧

```bash
# 启用详细日志
python src/alpha_new/main.py --log-level DEBUG

# 测试配置连通性
python -c "
from src.alpha_new.services.user_service import test_user_config
import asyncio
asyncio.run(test_user_config('config/pc_users.json'))
"

# 验证配置格式
python -c "
import json
with open('config/pc_users.json') as f:
    config = json.load(f)
    print('✅ 配置格式正确')
"
```

## 📞 获取帮助

如果在配置过程中遇到问题：

1. 查看日志文件 `logs/app.log`
2. 参考 [API文档](API_REFERENCE_MERGED.md)
3. 查看 [项目架构分析](PROJECT_ARCHITECTURE_ANALYSIS.md)
4. 提交Issue到项目仓库

---

**重要提醒**：请确保所有敏感信息（如session_id、auth_token等）不要泄露给他人，定期更换认证凭据以保证账户安全。 