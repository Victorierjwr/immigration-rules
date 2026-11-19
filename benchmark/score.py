#!/usr/bin/env python3
"""评测评分器：对比 agent 提交结果与 golden 期望（总分精确匹配 / gates 拦截匹配）。

用法：python benchmark/score.py submission.jsonl [--cases cases-zh.jsonl]
submission 行格式：{"case_id": "...", "total": 469} 或 {"case_id": "...", "blocked": ["language_clb7"]}
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("submission", help="agent 结果 JSONL")
    parser.add_argument("--cases", default=str(HERE / "cases-zh.jsonl"))
    args = parser.parse_args()

    expected = {}
    for line in Path(args.cases).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        c = json.loads(line)
        expected[c["case_id"]] = c["expected"]

    correct = skipped = total = 0
    for line in Path(args.submission).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        sub = json.loads(line)
        case_id = sub.get("case_id", "?")
        exp = expected.get(case_id)
        if exp is None:
            print(f"SKIP {case_id}: 不在评测集中")
            skipped += 1
            continue
        total += 1
        if "blocked" in exp:
            got = sorted(sub.get("blocked") or [])
            want = sorted(exp["blocked"])
            ok = set(want).issubset(set(got))
        else:
            ok = sub.get("total") == exp.get("total")
        if ok:
            correct += 1
        else:
            print(f"FAIL {case_id}: got {sub.get('total', sub.get('blocked'))}, expected {exp}")
    print(f"\n{correct}/{total} 正确" + (f"（另有 {skipped} 条不在评测集）" if skipped else ""))
    return 0 if total and correct == total else 1


if __name__ == "__main__":
    sys.exit(main())
