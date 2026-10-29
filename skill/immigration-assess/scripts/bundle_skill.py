#!/usr/bin/env python3
"""打包自包含 skill 分发包：skill + 引擎 + 规则 + schema 快照（zip）。

用途：让不想克隆整个仓库的用户也能直接用——解压即用，脚本向上查找引擎，
包内自带 engine/ rules/ schema/，不依赖任何外部路径。
产物：dist/immigration-assess-<日期>.zip

用法：python skill/immigration-assess/scripts/bundle_skill.py
"""
from __future__ import annotations

import shutil
import sys
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]          # 仓库根
SKILL_DIR = ROOT / "skill" / "immigration-assess"
DIST = ROOT / "dist"

# 包内需要的引擎侧文件（运行时实际消费的全部）
ENGINE_SRC = ROOT / "engine"
RULES_SRC = ROOT / "rules"
SCHEMA_SRC = ROOT / "schema" / "profile-schema-v0.json"

SKIP_DIRS = {"__pycache__", ".venv", ".git"}
SKIP_FILES = {".engine-root"}


def _walk_copy(src: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for item in sorted(src.iterdir()):
        if item.name in SKIP_DIRS or item.name in SKIP_FILES:
            continue
        if item.is_dir():
            _walk_copy(item, dest / item.name)
        else:
            shutil.copy2(item, dest / item.name)


def main() -> int:
    DIST.mkdir(parents=True, exist_ok=True)
    stamp = date.today().isoformat()
    zip_path = DIST / f"immigration-assess-{stamp}.zip"
    staging = DIST / f".staging-{stamp}"

    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir()

    # 布局：<bundle>/{SKILL.md, scripts, references, assets, engine, rules, schema}
    for entry in ("scripts", "references", "assets"):
        _walk_copy(SKILL_DIR / entry, staging / entry)
    shutil.copy2(SKILL_DIR / "SKILL.md", staging / "SKILL.md")
    _walk_copy(ENGINE_SRC, staging / "engine")
    _walk_copy(RULES_SRC, staging / "rules")
    (staging / "schema").mkdir(parents=True, exist_ok=True)
    shutil.copy2(SCHEMA_SRC, staging / "schema" / "profile-schema-v0.json")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(staging.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(staging))

    shutil.rmtree(staging)
    size_kb = zip_path.stat().st_size / 1024
    print(f"已打包：{zip_path.relative_to(ROOT)}（{size_kb:.0f} KB，自包含引擎+规则+schema）")
    print("用法：解压后运行 scripts/assess.py <画像.json> [--lang en|ja] [--as-of 日期]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
