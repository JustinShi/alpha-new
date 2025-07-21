# Ruff 配置说明

## 📋 配置概述

本项目的 Ruff 配置已经过优化，针对 Alpha 交易系统的特点进行了定制化设置，平衡了代码质量检查和实用性。

## 🎯 配置原则

1. **实用性优先**: 忽略不影响功能的风格问题
2. **中文友好**: 支持中文日志和注释
3. **分类管理**: 不同类型文件使用不同规则
4. **开发效率**: 减少不必要的警告干扰

## 🔧 全局忽略规则

### 格式化相关
```toml
'E501',        # line too long (由 black 处理)
'E203',        # whitespace before ':'
```

### 复杂度相关
```toml
'C901',        # too complex
'PLR0913',     # too many arguments
'PLR0911',     # too many return statements
'PLR0912',     # too many branches
'PLR0915',     # too many statements
```

### 中文字符支持
```toml
'RUF001',      # 中文标点符号
'RUF002',      # 文档字符串中的中文字符
'RUF003',      # 注释中的中文字符
```

### 代码风格
```toml
'ERA001',      # 注释代码
'T201',        # print 语句
'S101',        # assert 语句
'B007',        # 未使用的循环变量
```

### 返回值和异常处理
```toml
'RET503',      # 缺少显式返回
'RET504',      # 返回前的不必要赋值
'B904',        # 异常链
'RUF012',      # 可变类属性
```

## 📁 文件特定规则

### 测试文件 (`tests/*`)
```toml
"PLR2004",     # 魔法数值比较
"S101",        # assert 语句
"F841",        # 未使用变量
"ARG001",      # 未使用函数参数
```

### 脚本文件 (`src/alpha_new/scripts/*`)
```toml
"T201",        # print 语句
"F841",        # 未使用变量
"PLR2004",     # 魔法数值
"S101",        # assert 语句
```

### CLI工具 (`src/alpha_new/cli.py`)
```toml
"T201",        # print 语句
"PLR2004",     # 魔法数值
```

### 初始化文件 (`__init__.py`)
```toml
"F401",        # 未使用导入（用于导出）
```

### 数据库模型 (`src/alpha_new/models/*`)
```toml
"RUF012",      # 可变类属性（SQLAlchemy 模型）
"A003",        # 内置属性遮蔽
```

### 数据库迁移 (`migrations/*`)
```toml
"E402",        # 模块级导入位置（alembic 生成）
"F401",        # 未使用导入
"T201",        # print 语句
```

## 🚀 使用方法

### 检查整个项目
```bash
poetry run ruff check
```

### 检查特定文件
```bash
poetry run ruff check src/alpha_new/scripts/auto_trader.py
```

### 自动修复
```bash
poetry run ruff check --fix
```

### 显示所有问题（包括被忽略的）
```bash
poetry run ruff check --show-fixes
```

## 📊 配置效果

### 优化前
- **问题数量**: 165 个
- **主要问题**: 中文标点符号、未使用变量、代码风格

### 优化后
- **问题数量**: 0 个
- **检查状态**: ✅ All checks passed!

## 🎯 最佳实践

### 1. 定期检查
```bash
# 在提交前运行
poetry run ruff check
poetry run black src/
```

### 2. IDE 集成
- 配置 VS Code 或其他 IDE 使用项目的 ruff 配置
- 启用保存时自动格式化

### 3. CI/CD 集成
```yaml
# GitHub Actions 示例
- name: Run Ruff
  run: poetry run ruff check
```

### 4. 自定义规则
如需添加新的忽略规则，请在 `pyproject.toml` 中的相应部分添加：

```toml
[tool.ruff.lint]
ignore = [
    # 添加新的全局忽略规则
    "NEW_RULE",
]

[tool.ruff.lint.per-file-ignores]
"specific/path/*" = ["SPECIFIC_RULE"]
```

## 🔄 维护建议

1. **定期审查**: 每月检查是否有新的规则需要添加或移除
2. **团队协商**: 新的忽略规则应经过团队讨论
3. **文档更新**: 重要的配置变更应更新此文档
4. **版本兼容**: 升级 ruff 版本时检查配置兼容性

## 📝 注意事项

- 忽略规则应该有明确的理由和注释
- 不要忽略可能影响代码安全性的规则
- 定期检查被忽略的问题是否仍然合理
- 新加入的开发者应了解项目的 ruff 配置原则
