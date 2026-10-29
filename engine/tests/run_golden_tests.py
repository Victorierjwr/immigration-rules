#!/usr/bin/env python3
"""Golden tests 运行器：engine/tests/golden/<pathway>/*.yaml → 计算器结果比对。

规则改动必须全绿；期望值来自官方算例或人工对照官方页的推算（每案例带 source_url）。
用法：python -m engine.tests.run_golden_tests
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
GOLDEN_DIR = Path(__file__).resolve().parent / "golden"
RULES_DIR = ROOT / "rules"

sys.path.insert(0, str(ROOT))

from engine.gates import run_gates  # noqa: E402
from engine.profile_map import derived, str_keys  # noqa: E402

CALCULATORS = {
    "canada_ee_crs": "engine.calculators.canada_ee_crs",
    "japan_hsp_1": "engine.calculators.japan_hsp",
    "germany_chancenkarte": "engine.calculators.germany_chancenkarte",
}


def load_rule(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def find_rule(pathway: str) -> dict:
    for path in sorted(RULES_DIR.rglob("*.yaml")):
        if path.name == "process.yaml":
            continue
        data = load_rule(path)
        if data.get("pathway") == pathway:
            return data
    raise FileNotFoundError(f"规则文件缺失: pathway={pathway}")


def import_calculator(module: str):
    import importlib
    return importlib.import_module(module)


def run_case(case: dict, pathway: str) -> list[str]:
    errors = []
    profile = case["profile"]
    eff = derived(profile, ["CA", "JP", "DE"])
    rule = find_rule(pathway)
    scoring = str_keys(rule.get("scoring") or {})

    if case.get("expect_blocked"):
        # 门槛可能分散在同国目录的多个规则文件（如 gates.yaml 与 ee_crs.yaml 分开）
        all_gates: list[dict] = []
        for path in sorted((RULES_DIR / rule["country"]).glob("*.yaml")):
            if path.name == "process.yaml":
                continue
            all_gates += load_rule(path).get("gates") or []
        failures = run_gates(all_gates, {**profile, "derived": eff})
        blocked_ids = {f["id"] for f in failures}
        wanted = set(case["expect_blocked"])
        if not wanted.issubset(blocked_ids):
            errors.append(f"期望被拦截的门槛 {wanted}，实际拦截 {blocked_ids}")
        return errors

    calc_mod = import_calculator(CALCULATORS[pathway])
    result = calc_mod.calculate(profile, eff, scoring, as_of=case.get("as_of"))

    expected = case["expected"]
    if "total" in expected and result["total"] != expected["total"]:
        errors.append(f"总分 {result['total']} != 期望 {expected['total']}")
    for section, value in (expected.get("sections") or {}).items():
        got = (result.get("sections") or {}).get(section)
        if got != value:
            errors.append(f"分项 {section}: {got} != 期望 {value}")
    return errors


def main() -> int:
    failed_cases = 0
    total_cases = 0
    for case_dir in sorted(GOLDEN_DIR.iterdir()):
        if not case_dir.is_dir():
            continue
        pathway = case_dir.name
        for case_path in sorted(case_dir.glob("*.yaml")):
            total_cases += 1
            case = load_rule(case_path)
            errors = run_case(case, pathway)
            if errors:
                failed_cases += 1
                print(f"FAIL {case_path.relative_to(ROOT)}: {case.get('name', '?')}")
                for e in errors:
                    print(f"  - {e}")
            else:
                print(f"ok   {case_path.relative_to(ROOT)}: {case.get('name', '?')}")
    print(f"\n{total_cases - failed_cases}/{total_cases} 通过")
    return 1 if failed_cases else 0


if __name__ == "__main__":
    sys.exit(main())
