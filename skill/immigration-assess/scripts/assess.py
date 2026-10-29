#!/usr/bin/env python3
"""immigration-assess skill 主入口：定位仓库根，调用 engine.assess。

单一事实源原则：算分逻辑与规则数据永远在仓库 engine/ 与 rules/ 中，
本脚本只是薄封装——绝不复制计算代码（否则规则更新两边漂移）。
支持 ENGINE_ROOT 环境变量显式指定仓库根（skill 被复制到其他位置时）。
"""
import os
import sys
from pathlib import Path

def find_repo_root() -> Path | None:
    # 优先级：ENGINE_ROOT 环境变量 → skill 目录下 .engine-root 文件 → 向上寻找
    override = os.environ.get("ENGINE_ROOT")
    if override and (Path(override) / "engine" / "assess.py").exists():
        return Path(override)
    skill_dir = Path(__file__).resolve().parents[1]
    root_file = skill_dir / ".engine-root"
    if root_file.exists():
        candidate = Path(root_file.read_text(encoding="utf-8").strip())
        if (candidate / "engine" / "assess.py").exists():
            return candidate
    for parent in Path(__file__).resolve().parents:
        if (parent / "engine" / "assess.py").exists():
            return parent
    return None


REPO = find_repo_root()
if REPO is None:
    sys.exit(
        "未找到 immigration-rules 仓库根（engine/assess.py）。\n"
        "请将 skill 放在仓库内，或设置环境变量 ENGINE_ROOT=<仓库路径>。"
    )
sys.path.insert(0, str(REPO))


def _ensure_deps() -> None:
    """依赖缺失时自动用仓库 .venv 的解释器重跑——Agent 用哪个 Python 都能用。"""
    try:
        import jsonschema  # noqa: F401
        import yaml  # noqa: F401
        return
    except ImportError:
        pass
    venv = REPO / ".venv"
    for python in (venv / "Scripts" / "python.exe", venv / "bin" / "python"):
        if python.exists():
            os.execv(str(python), [str(python), *sys.argv])
    sys.exit("缺少依赖 jsonschema/pyyaml：请先安装（pip install jsonschema pyyaml），或使用带依赖的 Python 环境")


_ensure_deps()

if __name__ == "__main__":
    from engine.assess import main

    sys.exit(main())
