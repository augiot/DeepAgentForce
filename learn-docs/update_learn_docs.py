#!/usr/bin/env python3
"""
learn-docs 自动化工具

用法:
    python update_learn_docs.py [command]

命令:
    log         - 记录当前开发会话（基于 git 变更）
    summary     - 生成项目摘要
    init        - 初始化学习文档（已存在则跳过）
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

LEARN_DOCS_DIR = Path(__file__).parent
DEV_LOG = LEARN_DOCS_DIR / "01-dev-log.md"
PROJECT_ROOT = LEARN_DOCS_DIR.parent


def run_git(cmd: str) -> str:
    """执行 git 命令并返回输出"""
    try:
        result = subprocess.run(
            cmd.split(),
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {e}"


def get_recent_commits(count: int = 5) -> list:
    """获取最近的提交"""
    output = run_git(f"git log --oneline -{count}")
    commits = []
    for line in output.split("\n"):
        if line.strip():
            parts = line.split(" ", 1)
            if len(parts) == 2:
                commits.append({"hash": parts[0], "message": parts[1]})
    return commits


def get_uncommitted_changes() -> str:
    """获取未提交的变更"""
    return run_git("git status --short")


def get_diff_summary() -> str:
    """获取变更统计"""
    return run_git("git diff --stat HEAD")


def update_dev_log():
    """更新开发日志"""
    today = datetime.now().strftime("%Y-%m-%d")

    # 读取现有日志
    if DEV_LOG.exists():
        with open(DEV_LOG, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = "# 开发日志\n\n"

    # 获取 git 信息
    commits = get_recent_commits(3)
    changes = get_uncommitted_changes()

    # 构建更新内容
    update_section = f"## {today}\n\n"

    if changes:
        update_section += "### 未提交的变更\n```bash\n"
        update_section += changes + "\n```\n\n"

    if commits:
        update_section += "### 最近提交\n"
        for commit in commits:
            update_section += f"- `{commit['hash']}` {commit['message']}\n"
        update_section += "\n"

    # 检查是否已存在今日记录
    if f"## {today}" in content:
        print(f"⚠️  {today} 的记录已存在，跳过更新")
        return

    # 插入到现有内容之前
    new_content = content.replace("# 开发日志\n", f"# 开发日志\n\n{update_section}")

    with open(DEV_LOG, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"✅ 已更新开发日志：{DEV_LOG}")


def generate_summary():
    """生成项目摘要"""
    print("\n📊 DeepAgentForce 项目摘要\n")

    # 统计代码文件
    py_files = list(PROJECT_ROOT.rglob("*.py"))
    print(f"Python 文件数：{len(py_files)}")

    # 统计行数
    total_lines = 0
    for f in py_files:
        try:
            with open(f, "r", encoding="utf-8") as fp:
                total_lines += len(fp.readlines())
        except:
            pass
    print(f"Python 代码总行数：{total_lines}")

    # 最近提交
    commits = get_recent_commits(5)
    if commits:
        print("\n最近提交:")
        for c in commits:
            print(f"  {c['hash']} {c['message']}")

    print()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    command = sys.argv[1]

    if command == "log":
        update_dev_log()
    elif command == "summary":
        generate_summary()
    elif command == "init":
        print("✅ learn-docs 已存在")
    else:
        print(f"❌ 未知命令：{command}")
        print(__doc__)


if __name__ == "__main__":
    main()
