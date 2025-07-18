# 开发环境配置指南

本文档描述了 Alpha 交易系统的开发环境配置和最佳实践。

## 🚀 快速开始

### 1. 环境要求
- Python 3.13+
- Poetry (包管理器)
- Git

### 2. 安装开发环境
```bash
# 克隆项目
git clone <repository-url>
cd alpha-new

# 安装依赖和开发工具
make dev-install
# 或者
poetry install
poetry run pre-commit install
```

## 🛠️ 开发工具配置

### 代码质量工具

我们使用以下工具确保代码质量：

#### Ruff (代码检查和格式化)
- **配置文件**: `pyproject.toml` 中的 `[tool.ruff]` 部分
- **功能**: 替代 black, isort, flake8 等多个工具
- **运行**: `make lint` 或 `poetry run ruff check .`

#### MyPy (类型检查)
- **配置文件**: `pyproject.toml` 中的 `[tool.mypy]` 部分
- **功能**: 静态类型检查
- **运行**: `make type-check` 或 `poetry run mypy src/`

#### Pytest (测试框架)
- **配置文件**: `pyproject.toml` 中的 `[tool.pytest.ini_options]` 部分
- **功能**: 单元测试和集成测试
- **运行**: `make test` 或 `poetry run pytest`

#### Pre-commit (Git 钩子)
- **配置文件**: `.pre-commit-config.yaml`
- **功能**: 提交前自动运行代码质量检查
- **运行**: 自动运行，或手动 `make pre-commit`

## 📝 常用命令

我们提供了 Makefile 来简化常用操作：

```bash
# 查看所有可用命令
make help

# 开发环境设置
make dev-install

# 代码质量检查
make lint          # 代码检查
make lint-fix      # 自动修复问题
make format        # 代码格式化
make type-check    # 类型检查
make check         # 运行所有检查

# 测试
make test          # 运行测试
make test-cov      # 运行测试并生成覆盖率报告
make test-fast     # 跳过慢速测试

# 清理
make clean         # 清理缓存和构建文件

# 运行应用
make run           # 运行主应用
make run-example   # 运行示例
```

## 🔧 配置文件说明

### pyproject.toml
项目的主配置文件，包含：
- 项目元数据和依赖
- Ruff 配置（代码检查和格式化）
- MyPy 配置（类型检查）
- Pytest 配置（测试）
- Coverage 配置（测试覆盖率）

### .pre-commit-config.yaml
Pre-commit 钩子配置，包含：
- Ruff 检查和格式化
- MyPy 类型检查
- 基本文件检查
- YAML/TOML/JSON 格式检查

### Makefile
开发命令快捷方式，提供统一的开发体验。

## 📋 代码规范

### 代码风格
- 使用 Ruff 进行代码检查和格式化
- 行长度限制：88 字符
- 使用双引号
- 使用空格缩进（4个空格）

### 类型注解
- 所有函数必须有类型注解
- 使用现代 Python 类型语法（如 `list[str]` 而不是 `List[str]`）
- 使用 `X | None` 而不是 `Optional[X]`

### 导入规范
- 标准库导入在最前
- 第三方库导入在中间
- 本地模块导入在最后
- 每组之间用空行分隔

### 文档字符串
- 使用 Google 风格的文档字符串
- 所有公共函数和类都应该有文档字符串

## 🧪 测试规范

### 测试结构
```
tests/
├── unit/          # 单元测试
├── integration/   # 集成测试
└── conftest.py    # 测试配置
```

### 测试命名
- 测试文件：`test_*.py`
- 测试类：`Test*`
- 测试函数：`test_*`

### 测试标记
- `@pytest.mark.slow` - 慢速测试
- `@pytest.mark.integration` - 集成测试
- `@pytest.mark.unit` - 单元测试

## 🔒 安全考虑

- 不要在代码中硬编码敏感信息
- 使用环境变量或配置文件存储密钥
- 配置文件已添加到 `.gitignore`
- 使用 Bandit 进行安全检查（通过 Ruff 的 S 规则）

## 📦 依赖管理

### 核心依赖
- `httpx` - HTTP 客户端
- `websockets` - WebSocket 支持
- `pydantic` - 数据验证
- `rich` - 终端输出美化

### 开发依赖
- `pytest` - 测试框架
- `mypy` - 类型检查
- `ruff` - 代码检查和格式化
- `pre-commit` - Git 钩子

### 添加新依赖
```bash
# 生产依赖
poetry add package-name

# 开发依赖
poetry add --group dev package-name
```

## 🚀 部署准备

在部署前，确保：
1. 所有测试通过：`make test`
2. 代码质量检查通过：`make check`
3. 类型检查通过：`make type-check`
4. 构建成功：`make build`

## 📚 更多资源

- [Poetry 文档](https://python-poetry.org/docs/)
- [Ruff 文档](https://docs.astral.sh/ruff/)
- [MyPy 文档](https://mypy.readthedocs.io/)
- [Pytest 文档](https://docs.pytest.org/)
- [Pre-commit 文档](https://pre-commit.com/)
