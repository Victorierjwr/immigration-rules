"""德国机会卡（Chancenkarte, §20a AufenthG）计算器（纯函数，零依赖）。

参数来自 rules/germany/chancenkarte.yaml；无邀请轮——按 6 分门槛判定。
未入库输入显式列入 unsupported，绝不静默少算。
"""
from __future__ import annotations

import yaml
from pathlib import Path

from engine.profile_map import str_keys

RULE_PATH = Path(__file__).resolve().parents[2] / "rules" / "germany" / "chancenkarte.yaml"


def load_scoring() -> dict:
    return str_keys(yaml.safe_load(RULE_PATH.read_text(encoding="utf-8"))["scoring"])


def calculate(profile: dict, eff: dict, scoring: dict | None = None, as_of: str | None = None) -> dict:
    scoring = scoring or load_scoring()
    person = profile.get("person") or {}
    work = profile.get("work") or {}
    unsupported: list[str] = []

    # 语言（互斥取高）：德语 B2=3 / B1=2 / A2=1 / C1=3（与 B2 同分封顶）/ 英语 C1=1
    german = eff.get("german_level")
    german_pts = {"B2": 3, "B1": 2, "A2": 1, "C1": 3}.get(german or "", 0)
    eng_overall = eff.get("english_overall")
    english_c1_pts = 1 if (eng_overall is not None and eng_overall >= 7.0) else 0
    language_pts = max(german_pts, english_c1_pts)

    # 短缺职业经验（近 7 年 5 年=3 / 近 5 年 2 年=2）——短缺职业清单未入库，按 related 近似
    years = work.get("years_related", 0.0) or 0.0
    experience_pts = scoring["experience_shortage"]["5+"] if years >= 5 else (
        scoring["experience_shortage"]["2+"] if years >= 2 else 0
    )

    # 年龄：≤35=2 / 36-39=1
    age = eff["age_years"]
    age_pts = scoring["age"]["35-"] if age <= 35 else (scoring["age"]["40-"] if age <= 39 else 0)

    # 在德居留（近 5 年 ≥6 个月）
    stay_pts = scoring["stay_germany"] if (work.get("years_in") or {}).get("DE", 0.0) >= 0.5 else 0

    # 配偶
    spouse_pts = scoring["spouse"] if person.get("marital_status") in ("married", "common_law") else 0

    recognition_pts = 0
    unsupported.append("德国职业资格部分认定（4 分）：schema 无字段，v0 不计分")

    total = language_pts + experience_pts + age_pts + stay_pts + spouse_pts + recognition_pts
    eligible = total >= scoring["threshold_eligible"]

    return {
        "total": total,
        "sections": {
            "language": language_pts,
            "experience": experience_pts,
            "age": age_pts,
            "stay_germany": stay_pts,
            "spouse": spouse_pts,
            "recognition": recognition_pts,
        },
        "thresholds": {"eligible": scoring["threshold_eligible"]},
        "unsupported": unsupported,
        "breakdown": {
            "language": {"german": german, "points": language_pts},
            "experience": {"years": years, "points": experience_pts},
            "age": {"years": age, "points": age_pts},
            "stay_germany": {"years_in_DE": (work.get("years_in") or {}).get("DE", 0.0), "points": stay_pts},
            "spouse": {"status": person.get("marital_status"), "points": spouse_pts},
        },
    }
