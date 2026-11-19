#!/usr/bin/env python3
"""评测集生成器（形态 E）：golden 测试 → 自然语言 prompt + 机判期望。

每条评测 = prompt（自然语言问法 + 画像 JSON）+ 期望（总分精确匹配 / gates 拦截）。
agent 跑完评测后把结果写成 submission JSONL（case_id + total 或 blocked），用 score.py 评分。
用法：python benchmark/build_cases.py [--lang zh|en]
"""
import argparse
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "engine" / "tests" / "golden"

PROMPTS = {
    "zh": "请对以下画像做跨国移民评估，给出每个通路的总分或拦截结论。\n画像 JSON：\n{profile_json}\n\n只输出一个 JSON 数组，元素形如：{{\"pathway\": \"<通路名>\", \"total\": <整数>}}；若该通路被资格前置拦截，输出 {{\"pathway\": \"<通路名>\", \"blocked\": [<未过门槛 id 列表>]}}。",
    "en": "Assess the following profile for cross-border immigration eligibility, giving each pathway's total score or gate-blocked conclusion.\nProfile JSON:\n{profile_json}\n\nOutput a JSON array only, elements like: {{\"pathway\": \"<pathway>\", \"total\": <integer>}}; if the pathway is blocked by eligibility gates, output {{\"pathway\": \"<pathway>\", \"blocked\": [<failed gate ids>]}}.",
}


def build(lang: str) -> int:
    cases = []
    for case_dir in sorted(GOLDEN.iterdir()):
        if not case_dir.is_dir():
            continue
        pathway = case_dir.name
        for cp in sorted(case_dir.glob("*.yaml")):
            case = yaml.safe_load(cp.read_text(encoding="utf-8"))
            profile_json = json.dumps(case.get("profile", {}), ensure_ascii=False, indent=2)
            prompt = PROMPTS[lang].format(profile_json=profile_json)
            entry = {
                "case_id": f"{pathway}/{cp.stem}",
                "pathway": pathway,
                "as_of": case.get("as_of"),
                "prompt": prompt,
                "source_url": case.get("source_url", ""),
            }
            if case.get("expect_blocked"):
                entry["expected"] = {"blocked": sorted(case["expect_blocked"])}
            elif "total" in (case.get("expected") or {}):
                entry["expected"] = {"total": case["expected"]["total"]}
            else:
                continue
            cases.append(entry)
    out = Path(__file__).resolve().parent / f"cases-{lang}.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for c in cases:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"generated {len(cases)} cases -> {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--lang", choices=["zh", "en"], default="zh")
    sys_args = p.parse_args()
    raise SystemExit(build(sys_args.lang))
