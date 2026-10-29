"""assess CLI：画像 → 五段流程 → 资格矩阵报告（JSON / Markdown）。

用法：
  python -m engine.assess profile.json [--format md|json]

五段流程：画像校验 → gates 前置 → 确定性算分 → 动态对齐（gap）→ 结构化输出。
铁律：gates 未过不产分数；LLM 永不参与计算（本文件为纯 CLI，供 Skill/MCP 调用）。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine.gap import analyze, load_cutoffs  # noqa: E402
from engine.gates import run_gates  # noqa: E402
from engine.profile_map import derived  # noqa: E402

CALCULATORS = {
    "canada_ee_crs": "engine.calculators.canada_ee_crs",
    "japan_hsp_1": "engine.calculators.japan_hsp",
    "germany_chancenkarte": "engine.calculators.germany_chancenkarte",
}

DISCLAIMER = {
    "zh": """---

> **免责声明**：本报告为公开信息整理与确定性计算的结果，不构成移民、法律或签证建议。
> 政策随时可变且本工具可能存在滞后——请以各国官方发布为准，并咨询持牌专业人士
> （加拿大 RCIC / 澳洲 MARA / 日本行政书士 / 德国相关资格人员）。""",
    "en": """---

> **Disclaimer**: This report is compiled from public information and deterministic computation; it is not immigration, legal, or visa advice. Policies change and this tool may lag—verify with official sources and consult licensed professionals (Canada RCIC / Australia MARA / Japan accredited administrative scrivener / Germany qualified advisers).""",
    "ja": """---

> **免責事項**：本レポートは公開情報の整理と確定的計算の結果であり、移民・法律・ビザの助言ではありません。政策はいつでも変更され、本ツールに遅延がある可能性があります—各国公式情報を優先し、有資格専門家（カナダ RCIC / オーストラリア MARA / 日本 行政書士 / ドイツ 資格者）に相談してください。""",
}

# 固定标签本地化（规则数据文本——fail_output/unsupported 等——保持中文原样，
# 由 Agent 向非中文用户呈现时翻译；见 SKILL.md 与 output-guidelines.md）
LABELS = {
    "zh": {
        "title": "跨国移民资格评估报告", "date": "评估日期", "assess_note": "（年龄按评估日计）",
        "matrix": "资格矩阵", "score_unit": "分",
        "total": "总分", "sections": "分项", "unsupported": "未计入项（总分可能被低估）",
        "category_ref": "类别轮参考", "program_ref": "项目轮参考",
        "threshold": "门槛判定", "japan_note": "积分制通路——无邀请轮 cutoff，按 70/80 分门槛判定",
        "rule_version": "规则版本", "source": "官方来源", "next_steps": "下一步（条件式，非建议）",
        "median": "近 12 个月中位", "remedy_hint": "补足路径", "track": "轨道",
        "status": {"eligible": "✅ 可申请", "near": "⚠️ 接近", "far": "◻️ 差距大",
                   "blocked": "❌ 不满足", "info_only": "❔ 仅信息层"},
    },
    "en": {
        "title": "Cross-Border Immigration Eligibility Assessment Report",
        "date": "Assessment date", "assess_note": " (age computed at assessment date)",
        "matrix": "Eligibility matrix", "score_unit": "pts",
        "total": "Total score", "sections": "Sections", "unsupported": "Not-counted items (score may be underestimated)",
        "category_ref": "Category draw reference", "program_ref": "Program draw reference",
        "threshold": "Threshold assessment",
        "japan_note": "Points-based pathway—no invitation-round cutoff; judged by 70/80-point thresholds",
        "rule_version": "Rule version", "source": "Official source",
        "next_steps": "Next steps (conditional, not advice)", "median": "12-month median",
        "remedy_hint": "How to fix", "track": "Track",
        "status": {"eligible": "✅ eligible", "near": "⚠️ close", "far": "◻️ far below",
                   "blocked": "❌ not eligible", "info_only": "❔ info only"},
    },
    "ja": {
        "title": "国境を越えた移住資格評価レポート", "date": "評価日", "assess_note": "（評価日時点で年齢計算）",
        "matrix": "資格マトリクス", "score_unit": "点",
        "total": "合計点", "sections": "内訳", "unsupported": "未算入項目（合計点は過小評価の可能性あり）",
        "category_ref": "カテゴリー抽選リファレンス", "program_ref": "プロジェクト抽選リファレンス",
        "threshold": "thresholds 判定",
        "japan_note": "ポイント制—招待ラウンド cutoff なし。70/80 点の thresholds で判定",
        "rule_version": "ルール版", "source": "公式ソース",
        "next_steps": "次のステップ（条件付き・助言ではない）", "median": "直近12ヶ月中央値",
        "remedy_hint": "解消方法", "track": "トラック",
        "status": {"eligible": "✅ 申請可", "near": "⚠️ 近い", "far": "◻️ 大きな差距",
                   "blocked": "❌ 不满足", "info_only": "❔ 情報層のみ"},
    },
}


def load_profile(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_profile(profile: dict) -> list[str]:
    schema = json.loads((ROOT / "schema" / "profile-schema-v0.json").read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    return [e.message for e in validator.iter_errors(profile)]


def load_rules(country: str) -> dict:
    """同国目录全部规则文件（排除 process 与 CSV）。"""
    country_dir = ROOT / "rules" / country
    rules = []
    for path in sorted(country_dir.glob("*.yaml")):
        if path.name == "process.yaml":
            continue
        rules.append(yaml.safe_load(path.read_text(encoding="utf-8")))
    return rules


def all_gates(rules: list[dict]) -> list[dict]:
    gates = []
    for rule in rules:
        gates += rule.get("gates") or []
    return gates


def confidence(rule: dict, golden_dirs: set[str]) -> str:
    last = date.fromisoformat(str(rule["last_verified"]))
    age_days = (date.today() - last).days
    if rule.get("pending_changes") or age_days > 90:
        return "○"
    if age_days > 180:
        return "○"
    if rule["pathway"] in golden_dirs:
        return "●"
    return "◐"


def assess_country(country: str, profile: dict, eff: dict, as_of: str | None = None) -> list[dict]:
    rules = load_rules(country)
    results = []
    for rule in rules:
        pathway = rule["pathway"]
        if rule.get("meta", {}).get("assessment_mode") == "info_layer":
            # 信息层通路：不做评估，展示官方链接与邀请轮历史
            rounds = load_cutoffs(ROOT / "rules" / country / "cutoff_history.csv")
            recent = sorted(rounds, key=lambda r: r["draw_date"], reverse=True)[:5]
            results.append({
                "pathway": pathway,
                "country": country,
                "status": "info_only",
                "info": {"pathways": rule["meta"].get("pathways", []), "rounds": recent},
                "source_url": rule["source_url"],
                "confidence": confidence(rule, _golden_dirs()),
            })
            continue
        if pathway not in CALCULATORS:
            continue  # categories/gates 类规则文件不评估
        failures = run_gates(all_gates(rules), {**profile, "derived": eff})
        if failures:
            results.append({
                "pathway": pathway,
                "country": country,
                "status": "blocked",
                "reason_code": "GATE_FAIL_" + failures[0]["id"].upper().replace("-", "_"),
                "reasons": failures,
                "source_url": rule["source_url"],
                "confidence": confidence(rule, _golden_dirs()),
            })
            continue

        import importlib
        calc_mod = importlib.import_module(CALCULATORS[pathway])
        scoring = calc_mod.load_scoring()
        result = calc_mod.calculate(profile, eff, scoring, as_of=as_of)

        if country in ("japan", "germany"):
            # 门槛制通路——无邀请轮 cutoff，按官方门槛判定
            thresholds = result.get("thresholds") or {}
            threshold = next(iter(thresholds.values())) if thresholds else 6
            gap = {"status": "OK", "track": result.get("track"),
                   "note": f"门槛制通路——无邀请轮 cutoff，按 {threshold} 分门槛判定"}
            if result["total"] >= threshold:
                status, reason_code = "eligible", f"SCORE_OK_THRESHOLD_{threshold}"
            else:
                status, reason_code = "far", "SCORE_BELOW_THRESHOLD"
        else:
            gap = analyze(result["total"], country, category=None)
            cat = gap["category"]
            if cat["status"] == "CATEGORY_NO_DRAWS":
                status, reason_code = "far", "CATEGORY_NO_DRAWS"
            else:
                g = cat["gap"]
                if g is not None and g >= 0:
                    status, reason_code = "eligible", "SCORE_AVAILABLE"
                elif g is not None and -10 < g < 0:
                    status, reason_code = "near", "SCORE_BELOW_CUTOFF"
                else:
                    status, reason_code = "far", "SCORE_BELOW_CUTOFF"

        results.append({
            "pathway": pathway,
            "country": country,
            "status": status,
            "score": result["total"],
            "sections": result["sections"],
            "unsupported": result.get("unsupported", []),
            "breakdown": result.get("breakdown", {}),
            "gap": gap,
            "reason_code": reason_code,
            "source_url": rule["source_url"],
            "confidence": confidence(rule, _golden_dirs()),
            "rule_version": {"effective_date": rule["effective_date"],
                             "last_verified": rule["last_verified"]},
        })
    return results


def _golden_dirs() -> set[str]:
    golden = ROOT / "engine" / "tests" / "golden"
    if not golden.exists():
        return set()
    return {p.name for p in golden.iterdir() if p.is_dir()}


def render_markdown(profile: dict, results: list[dict], lang: str = "zh") -> str:
    L = LABELS.get(lang, LABELS["zh"])
    lines = [f"# {L['title']}", f"{L['date']}：{date.today().isoformat()}{L['assess_note']}", ""]
    lines.append(f"## {L['matrix']}")
    lines.append("")
    icons = L["status"]
    for r in sorted(results, key=lambda x: (0 if x["status"] == "eligible" else 1, -x.get("score", 0))):
        icon = icons.get(r["status"], r["status"])
        score_part = f" {r['score']} {L['score_unit']}" if r.get("score") is not None else ""
        lines.append(f"- **{r['country']} · {r['pathway']}**：{icon}{score_part}　[{r['confidence']}]")
    lines.append("")
    for r in results:
        lines.append(f"## {r['country']} · {r['pathway']}")
        lines.append("")
        if r["status"] == "info_only":
            info = r.get("info") or {}
            lines.append("- ❔ 仅信息层——改革窗口期不做评估，仅整理官方信息")
            for p in info.get("pathways") or []:
                lines.append(f"  - {p.get('name', p.get('id'))}：{p.get('official_url', '')}")
            rounds = info.get("rounds") or []
            if rounds:
                lines.append("  - 近期邀请轮：")
                for rw in rounds:
                    cut = rw.get("cutoff") if rw.get("cutoff") is not None else "未公布"
                    inv = rw.get("invitations") if rw.get("invitations") is not None else "?"
                    lines.append(f"    - {rw['draw_date']}（{rw.get('category') or rw['round_type']}）：邀请 {inv}，cutoff {cut}")
            lines.append(f"  - {L['source']}：{r['source_url']}")
            lines.append("")
            continue
        if r["status"] == "blocked":
            for f in r["reasons"]:
                lines.append(f"- ❌ **{f['id']}**：{f['fail_output']}")
                if f.get("remedy_hint"):
                    lines.append(f"  - {L['remedy_hint']}：{f['remedy_hint']}")
                if f.get("source_url"):
                    lines.append(f"  - {L['source']}：{f['source_url']}")
        else:
            b = r.get("breakdown") or {}
            lines.append(f"- {L['total']}：**{r['score']}**（{L['sections']}：{r.get('sections', {})}）")
            for key, val in b.items():
                lines.append(f"- {key}：{val}")
            if r.get("unsupported"):
                lines.append(f"- ⚠️ {L['unsupported']}：{'；'.join(r['unsupported'])}")
            gap = r.get("gap") or {}
            if r["country"] in ("japan", "germany"):
                if gap.get("status") == "OK" and gap.get("track") is not None:
                    lines.append(f"- {L['threshold']}：{gap.get('note', '')} {L['track']} {gap['track']}")
                else:
                    lines.append(f"- {L['threshold']}：{gap.get('note', '')}")
            else:
                cat = gap.get("category") or {}
                if cat["status"] == "OK":
                    draw = cat["latest_draw"]
                    lines.append(f"- {L['category_ref']}：最近 {draw['draw_date']}（{draw['category']}）cutoff {cat['cutoff']}，"
                                 f"gap = {cat['gap']}，{L['median']} {cat.get('median_12mo')}")
                else:
                    lines.append(f"- {L['category_ref']}：{cat['message']}")
                general = gap.get("general")
                if general and general["status"] == "OK":
                    draw = general["latest_draw"]
                    lines.append(f"- {L['program_ref']}：最近 {draw['draw_date']}（{draw['category'] or '全项目'}）cutoff {general['cutoff']}，gap = {general['gap']}")
            lines.append(f"- {L['rule_version']}：effective {r['rule_version']['effective_date']} / 核对 {r['rule_version']['last_verified']}　置信度 [{r['confidence']}]")
            lines.append(f"- {L['source']}：{r['source_url']}")
        lines.append("")
    lines.append(DISCLAIMER.get(lang, DISCLAIMER["zh"]))
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("profile", help="画像 JSON 文件")
    parser.add_argument("--format", choices=["md", "json"], default="md")
    parser.add_argument("--lang", choices=["zh", "en", "ja"], default="zh", help="报告语言（固定标签本地化；规则数据文本保持中文，由 Agent 翻译呈现）")
    parser.add_argument("--as-of", help="评估基准日期 YYYY-MM-DD（默认今天；影响 CRS 双制切换）")
    args = parser.parse_args()

    profile = load_profile(Path(args.profile))
    errors = validate_profile(profile)
    if errors:
        print("画像不符合 canonical 画像 schema：", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 2

    eff = derived(profile, ["CA", "JP", "DE", "AU"])
    results = assess_country("canada", profile, eff, as_of=args.as_of) + \
        assess_country("japan", profile, eff, as_of=args.as_of) + \
        assess_country("germany", profile, eff, as_of=args.as_of) + \
        assess_country("australia", profile, eff, as_of=args.as_of)
    if args.format == "json":
        print(json.dumps({"profile_summary": {k: v for k, v in profile.items() if k != "person"},
                          "results": results, "lang": args.lang}, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(profile, results, lang=args.lang))
    return 0


if __name__ == "__main__":
    sys.exit(main())
