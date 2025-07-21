#!/usr/bin/env python3
"""
配置验证和修复脚本 - 验证并自动修复pyproject.toml配置
"""

from pathlib import Path
import subprocess
import sys


def run_command(
    cmd: list[str], description: str, capture_output: bool = True
) -> tuple[bool, str]:
    """运行命令并返回是否成功和输出"""
    print(f"\n🔍 {description}...")
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        if result.returncode == 0:
            print(f"✅ {description} - 通过")
            return True, result.stdout if capture_output else ""
        else:
            print(f"❌ {description} - 失败")
            if capture_output:
                print(f"错误输出: {result.stderr}")
                return False, result.stderr
            return False, ""
    except Exception as e:
        print(f"❌ {description} - 异常: {e}")
        return False, str(e)


def fix_code_formatting():
    """自动修复代码格式"""
    print("\n🔧 自动修复代码格式...")

    # 使用ruff自动修复
    success, _ = run_command(
        ["poetry", "run", "ruff", "check", "--fix", "src/alpha_new/"], "Ruff 自动修复"
    )

    # 使用black格式化
    success2, _ = run_command(
        ["poetry", "run", "black", "src/alpha_new/"], "Black 代码格式化"
    )

    return success and success2


def main():
    """主函数"""
    print("🚀 开始验证和优化 pyproject.toml 配置...")

    # 首先尝试自动修复格式问题
    print("\n📝 步骤1: 自动修复代码格式")
    fix_code_formatting()

    # 然后验证配置
    print("\n🔍 步骤2: 验证配置")
    tests = [
        (
            ["poetry", "run", "ruff", "check", "src/alpha_new/utils/__init__.py"],
            "Ruff 配置验证",
        ),
        (
            ["poetry", "run", "black", "--check", "src/alpha_new/utils/__init__.py"],
            "Black 配置验证",
        ),
        (["poetry", "run", "mypy", "src/alpha_new/utils/__init__.py"], "MyPy 配置验证"),
    ]

    passed = 0
    total = len(tests)

    for cmd, description in tests:
        success, _ = run_command(cmd, description)
        if success:
            passed += 1

    print(f"\n📊 验证结果: {passed}/{total} 通过")

    if passed == total:
        print("🎉 所有配置验证通过！")
        return 0
    else:
        print("⚠️ 部分配置仍需手动修复")
        return 1


if __name__ == "__main__":
    sys.exit(main())
