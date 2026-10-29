#!/usr/bin/env python3
"""Validate rule YAMLs, profile fixtures and cutoff CSVs against schema v0.

Hard fails (exit 1): schema violations, effective_date in the future,
duplicate gate ids, last_verified older than STALE_FAIL_DAYS.
Warnings (exit 0, stderr): last_verified older than STALE_WARN_DAYS.

Usage: python scripts/validate_rules.py   # repo root anywhere inside
"""
import csv
import json
import sys
from datetime import date
from pathlib import Path

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schema"
EXAMPLES_DIR = SCHEMA_DIR / "examples"
RULES_DIR = ROOT / "rules"
STALE_WARN_DAYS = 90
STALE_FAIL_DAYS = 180

# rules/ 下 process.yaml 走独立 schema（Phase 2 引入），现阶段跳过
SKIP_FILES = {"process.yaml"}


def load_schema(name: str) -> dict:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def make_validator(schema: dict) -> jsonschema.protocols.Validator:
    return jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())


def schema_errors(validator, data) -> list[str]:
    return [f"schema: {list(e.absolute_path)}: {e.message}" for e in validator.iter_errors(data)]


def days_since(iso_date: str) -> int:
    return (date.today() - date.fromisoformat(str(iso_date))).days


def validate_rule_file(path: Path, validator) -> tuple[list[str], list[str]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    errors = schema_errors(validator, data)
    warnings = []

    last_verified = data.get("last_verified")
    if last_verified:
        n = days_since(last_verified)
        if n > STALE_FAIL_DAYS:
            errors.append(f"staleness: last_verified {last_verified} 已 {n} 天未核对（>{STALE_FAIL_DAYS}，阻断）")
        elif n > STALE_WARN_DAYS:
            warnings.append(f"last_verified {last_verified} 已 {n} 天未核对（>{STALE_WARN_DAYS}，输出将降级为待复核）")

    effective = data.get("effective_date")
    if effective and date.fromisoformat(str(effective)) > date.today():
        errors.append(f"effective_date {effective} 晚于今天：现行生效日期不能是未来")

    gate_ids = [g.get("id") for g in (data.get("gates") or [])]
    dupes = sorted({g for g in gate_ids if gate_ids.count(g) > 1})
    if dupes:
        errors.append(f"gate id 重复: {dupes}")

    return errors, warnings


def validate_cutoff_csv(path: Path, validator) -> list[str]:
    errors = []
    with path.open(newline="", encoding="utf-8") as f:
        for lineno, row in enumerate(csv.DictReader(f), start=2):
            if not any((v or "").strip() for v in row.values()):
                continue
            record = {
                "draw_date": row.get("draw_date") or None,
                "round_type": row.get("round_type") or None,
                "category": row.get("category") or None,
                # 千分位逗号（如 "3,500"）是维护者常见粘贴习惯——先剥离再解析
                "invitations": int(row["invitations"].replace(",", "")) if (row.get("invitations") or "").strip() else None,
                "cutoff": float(row["cutoff"].replace(",", "")) if (row.get("cutoff") or "").strip() else None,
                "country": row.get("country") or None,
                "source_url": row.get("source_url") or None,
                "notes": row.get("notes") or None,
            }
            errors += [f"row {lineno}: {msg}" for msg in schema_errors(validator, record)]
    return errors


def iter_yaml_by_prefix(directory: Path, prefix: str):
    return sorted(directory.glob(f"{prefix}*.yaml")) if directory.exists() else []


def main() -> int:
    rule_validator = make_validator(load_schema("rule-schema-v0.json"))
    profile_validator = make_validator(load_schema("profile-schema-v0.json"))
    cutoff_validator = make_validator(load_schema("cutoff-record-v0.json"))

    failed = False

    rule_files = [
        p for p in sorted(RULES_DIR.rglob("*.y*ml")) if p.name not in SKIP_FILES
    ] if RULES_DIR.exists() else []
    if not rule_files:
        print("rules/: 暂无规则文件（Phase 0 骨架），跳过")
    for path in rule_files:
        errors, warnings = validate_rule_file(path, rule_validator)
        failed |= bool(errors)
        _report(path, errors, warnings)

    csv_files = sorted(RULES_DIR.rglob("cutoff_history*.csv")) if RULES_DIR.exists() else []
    for path in csv_files:
        errors = validate_cutoff_csv(path, cutoff_validator)
        failed |= bool(errors)
        _report(path, errors, [])

    # fixtures 必须始终合法，否则 schema 或样例被改坏
    for path in iter_yaml_by_prefix(EXAMPLES_DIR, "rule-"):
        errors, warnings = validate_rule_file(path, rule_validator)
        failed |= bool(errors)
        _report(path, errors, warnings)
    for path in iter_yaml_by_prefix(EXAMPLES_DIR, "profile-"):
        errors = schema_errors(profile_validator, yaml.safe_load(path.read_text(encoding="utf-8")))
        failed |= bool(errors)
        _report(path, errors, [])
    for path in EXAMPLES_DIR.glob("cutoff-*.csv") if EXAMPLES_DIR.exists() else []:
        errors = validate_cutoff_csv(path, cutoff_validator)
        failed |= bool(errors)
        _report(path, errors, [])

    print("\nFAIL" if failed else "\nOK")
    return 1 if failed else 0


def _report(path: Path, errors: list[str], warnings: list[str]) -> None:
    rel = path.relative_to(ROOT)
    for w in warnings:
        print(f"WARNING {rel}: {w}", file=sys.stderr)
    if errors:
        print(f"FAIL {rel}")
        for e in errors:
            print(f"  - {e}")
    else:
        print(f"ok   {rel}")


if __name__ == "__main__":
    sys.exit(main())
