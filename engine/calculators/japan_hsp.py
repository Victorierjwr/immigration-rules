"""日本高度専門職1号（ロ）积分计算器（纯函数，零依赖）。

参数全部来自 rules/japan/hsp_points.yaml；未支持加算显式列入 unsupported，绝不静默少算。
"""
from __future__ import annotations

import yaml
from pathlib import Path

from engine.profile_map import str_keys

RULE_PATH = Path(__file__).resolve().parents[2] / "rules" / "japan" / "hsp_points.yaml"


def load_scoring() -> dict:
    return str_keys(yaml.safe_load(RULE_PATH.read_text(encoding="utf-8"))["scoring"])


def _education_points(scoring: dict, degree: str | None) -> int:
    table = scoring["education"]
    if degree in table:
        return table[degree]
    return 0


def _experience_bucket(years: float | None) -> str | None:
    if not years:
        return None
    if years >= 10:
        return "10+"
    if years >= 7:
        return "7-10"
    if years >= 5:
        return "5-7"
    if years >= 3:
        return "3-5"
    return None


def _age_bucket(age: int) -> str:
    if age < 30:
        return "lt30"
    if age < 35:
        return "30-34"
    if age < 40:
        return "35-39"
    return "40+"


def _income_bucket(amount_jpy: float | None, table: dict) -> int:
    if amount_jpy is None:
        return 0
    man = amount_jpy / 10000.0  # 円 → 万円
    for bracket in sorted(table.keys(), key=lambda b: float(b.rstrip("+")), reverse=True):
        threshold = float(bracket.rstrip("+"))
        if man >= threshold:
            return table[bracket]
    return 0


def calculate(profile: dict, eff: dict, scoring: dict | None = None, as_of: str | None = None) -> dict:
    # as_of 仅为与 canada_ee_crs 保持接口一致；日本 HSP 规则不随日期切换
    scoring = scoring or load_scoring()
    education_block = profile.get("education") or {}
    work_block = profile.get("work") or {}
    language_block = profile.get("language") or {}

    degree = education_block.get("highest_degree")
    education_points = _education_points(scoring, degree)
    jp_degree_bonus = scoring["foreign_degree_bonus"] if education_block.get("country") == "JP" else 0

    years = work_block.get("years_related", 0.0) or 0.0
    exp_bucket = _experience_bucket(years)
    experience_points = scoring["years_of_experience"].get(exp_bucket, 0) if exp_bucket else 0

    age = eff["age_years"]
    age_points = scoring["age"][_age_bucket(age)]

    income = work_block.get("income_annual") or {}
    income_points = 0
    if income.get("currency") == "JPY":
        income_points = _income_bucket(income.get("amount"), scoring["income"][_age_bucket(age)])

    other_lang = language_block.get("other") or {}
    jlpt = str(other_lang.get("jlpt", "")).upper()
    jlpt_points = scoring["japanese"].get(jlpt.lower(), 0)

    total = education_points + jp_degree_bonus + experience_points + age_points + income_points + jlpt_points
    thresholds = scoring["thresholds"]
    track = "pr_1y" if total >= thresholds["pr_1y"] else ("pr_3y" if total >= thresholds["pr_3y"] else None)

    return {
        "total": total,
        "sections": {
            "education": education_points,
            "jp_degree_bonus": jp_degree_bonus,
            "experience": experience_points,
            "age": age_points,
            "income": income_points,
            "japanese": jlpt_points,
        },
        "track": track,
        "thresholds": thresholds,
        "unsupported": [
            "特别加算（研究实绩/资格/大学排名/R&D/投资运用等）——见规则 meta.unsupported",
            "イ/ハ 两个类别独立积分表——v0 仅 ロ",
        ],
        "breakdown": {
            "education": {"degree": degree, "points": education_points},
            "experience": {"years": years, "bucket": exp_bucket, "points": experience_points},
            "age": {"years": age, "bucket": _age_bucket(age), "points": age_points},
            "income": {"amount_jpy": income.get("amount"), "points": income_points},
            "japanese": {"jlpt": jlpt, "points": jlpt_points},
        },
    }
