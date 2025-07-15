# Alpha交易系统+空投领取系统

一个基于币安Alpha交易平台的本地交易工具，支持订单管理、空投查询、多账号管理等功能。

## 功能特性

- 🔧 **订单管理**: 下单、撤单、查询订单历史
- 🎁 **空投管理**: 查询空投、自动领取空投
- 👤 **多账号支持**: 本地管理多个用户会话
- 🔄 **快速切换**: 支持用户会话快速切换
- 📊 **钱包查询**: 实时查询钱包余额
- 🛡️ **本地存储**: 会话数据本地保存，安全可靠

## 项目结构

```
alpha-new/
├── .venv/                  # 虚拟环境
├── config/                 # 配置文件目录
│   ├── airdrop_config.yaml    # 空投配置
│   ├── proxies.txt            # 代理服务器列表  
│   └── config_template.toml   # 配置文件模板
├── data/                   # 运行时数据目录
│   ├── users_session.db    # 用户会话数据库
│   └── ...                 # 其他数据文件 (如 cookies.json)
├── docs/                   # 项目文档
├── logs/                   # 日志文件目录
│   └── ws_monitor.log      # WebSocket监控日志
├── scripts/                # 辅助脚本
├── src/                    # 核心源代码
│   ├── api_clients/        # API客户端
│   ├── models/             # 数据模型
│   ├── services/           # 业务逻辑服务
│   ├── utils/              # 工具函数
│   └── main.py             # 项目主入口
├── tests/                  # 测试代码
├── .gitignore              # Git忽略配置
├── pyproject.toml          # 项目构建和依赖配置
└── README.md               # 项目说明文档
```

## 部署和运行

### 环境要求

*   Python 3.8+

### 安装依赖

1.  **创建并激活虚拟环境 (推荐)**:
    ```bash
    python -m venv .venv
    # Windows
    .venv\Scripts\activate
    # macOS/Linux
    source .venv/bin/activate
    ```
2.  **安装项目依赖**:
    项目依赖已在 `pyproject.toml` 中定义。使用以下命令进行安装：
    ```bash
    pip install .
    ```
    ```

### 配置

项目配置位于 `config/` 目录下。

*   **配置文件管理**:
*   **`proxies.txt`**: 存放代理列表，每行一个。

### 运行项目

项目入口为 `src/main.py`。

```bash
python src/main.py
```

### 日志

项目日志将输出到控制台，并保存到 `logs/ws_monitor.log` 文件中。
