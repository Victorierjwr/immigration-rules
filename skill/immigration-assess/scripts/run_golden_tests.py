#!/usr/bin/env python3
"""immigration-assess skill 的 golden 回归入口（薄封装）。

规则数据改动后跑一遍，全绿才能发布——SKILL.md 铁律「算分只走脚本」的守护。
"""
import os
import sys
from pathlib import Path

def find_repo_root() -> Path | None:
    override = os.environ.get("ENGINE_ROOT")
    if override and (Path(override) / "engine" / "assess.py").exists():
        return Path(override)
    skill_dir = Path(__file__).resolve().parents[1]
    root_file = skill_dir / ".engine-root"
    if root_file.exists():
        candidate = Path(root_file.read_text(encoding="utf-8").strip())
        if (candidate / "engine" / "tests" / "run_golden_tests.py").exists():
            return candidate
    for parent in Path(__file__).resolve().parents:
        if (parent / "engine" / "tests" / "run_golden_tests.py").exists():
            return parent
    return None


REPO = find_repo_root()
if REPO is None:
    sys.exit("未找到仓库根（engine/tests/run_golden_tests.py）")
sys.path.insert(0, str(REPO))


def _ensure_deps() -> None:
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
    from engine.tests.run_golden_tests import main

    sys.exit(main())
