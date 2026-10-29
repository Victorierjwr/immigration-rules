"""加拿大 EE CRS 计算器（纯函数，零依赖）。

规则参数全部来自 rules/canada/ee_crs.yaml（不硬编码政策数字）；
未支持项显式计入 unsupported 清单，绝不静默少算。
"""
from __future__ import annotations

import yaml
from pathlib import Path

from engine.profile_map import ABILITIES, clb_from_test, str_keys

RULE_PATH = Path(__file__).resolve().parents[2] / "rules" / "canada" / "ee_crs.yaml"


def load_scoring() -> dict:
    return str_keys(yaml.safe_load(RULE_PATH.read_text(encoding="utf-8"))["scoring"])


def _education_bucket(degree: str | None) -> str:
    return {"phd": "phd", "master": "master", "bachelor": "bachelor",
            "diploma": "two_year", "other": "secondary"}.get(degree or "", "less_than_secondary")


def _cdn_work_bucket(years: float | None) -> str:
    if not years:
        return "none"
    return "5+" if years >= 5 else str(int(years))


def _foreign_bucket(years: float | None) -> str | None:
    if not years:
        return None
    return "three_plus_years" if years >= 3 else "one_two_years"


def _age_points(table: dict, age: int) -> int:
    if "45+" in table and age >= 45:
        return table["45+"]
    if age < 18:
        return 0
    # YAML 整数键（18）与范围键（"20-29"）并存
    for key in (str(age), int(age)):
        if key in table:
            return table[key]
    if "20-29" in table and 20 <= age <= 29:
        return table["20-29"]
    return 0


def _first_lang_points(table: dict, clb: int | None) -> int:
    if clb is None:
        return 0
    if clb >= 10:
        return table["10+"]
    if clb == 9:
        return table["9"]
    if clb == 8:
        return table["8"]
    if clb == 7:
        return table["7"]
    if clb == 6:
        return table["6"]
    if clb in (4, 5):
        return table["4-5"]
    return table["below4"]


def _second_lang_points(table: dict, clb: int | None) -> int:
    if clb is None:
        return 0
    if clb >= 9:
        return table["9+"]
    if 7 <= clb <= 8:
        return table["7-8"]
    if 5 <= clb <= 6:
        return table["5-6"]
    return table["below4"]


def _spouse_lang_points(table: dict, clb: int | None) -> int:
    return _second_lang_points(table, clb) if clb is not None and clb >= 5 else 0


def _lang_condition(clb: dict) -> str:
    vals = [v for v in clb.values() if v is not None]
    if not vals:
        return "none"
    if all(v >= 9 for v in vals):
        return "all_9_plus"
    if all(v >= 7 for v in vals):
        return "one_under_9"
    return "below7"


def _tr_edu_row(edu: str) -> str | None:
    # 核心教育桶 → transferability 行名（官方表：bachelor 属「1年+高等教育」行）
    return {
        "phd": "doctoral",
        "master": "master_professional",
        "bachelor": "one_year_post_secondary",
        "two_year": "one_year_post_secondary",
        "one_year": "one_year_post_secondary",
        "secondary": None,
        "less_than_secondary": None,
    }.get(edu)


def calculate(profile: dict, eff: dict, scoring: dict | None = None, as_of: str | None = None) -> dict:
    scoring = scoring or load_scoring()
    regime = "new" if as_of and as_of >= str(scoring.get("regime_switch", {}).get("date", "2026-11-03")) else "current"
    person = profile.get("person") or {}
    edu_block = profile.get("education") or {}
    work_block = profile.get("work") or {}
    language_block = profile.get("language") or {}
    spouse = person.get("spouse_profile") or {}
    has_spouse = person.get("marital_status") in ("married", "common_law") and bool(spouse)
    base = "spouse" if has_spouse else "single"

    age = eff["age_years"]
    unsupported: list[str] = []

    # ---- 核心人力资本 ----
    core = _age_points(scoring["age"][base], age)
    edu = _education_bucket(edu_block.get("highest_degree"))
    core += scoring["education"][base].get(edu, 0)

    eng = language_block.get("english") or {}
    french = language_block.get("french") or {}
    first_lang, second_lang = "english", "english"
    if eng.get("test") == "none" and french.get("test") != "none":
        first_lang = "french"
    elif french.get("test") != "none" and eng.get("test") != "none":
        second_lang = "french"

    clb_eng = clb_from_test(eng) if eng.get("test") else {a: None for a in ABILITIES}
    clb_second = clb_from_test(french) if french.get("test") else {a: None for a in ABILITIES}

    if first_lang == "english":
        core += sum(_first_lang_points(scoring["language_first"][base], clb_eng[a]) for a in ABILITIES)
        if second_lang == "french":
            unsupported.append("第二官方语言（法语 NCLC）：TEF/TCF→NCLC 对照表未入库，v0 不计分")
        else:
            core += sum(_second_lang_points(scoring["language_second"][base], clb_second[a]) for a in ABILITIES)
    else:
        unsupported.append("第一官方语言为法语：NCLC 换算未入库，核心语言分 v0 不计")

    cdn_years = work_block.get("years_in", {}).get("CA", 0.0) if isinstance(work_block.get("years_in"), dict) else 0.0
    cdn_work_points = scoring["cdn_work_experience"][base].get(_cdn_work_bucket(cdn_years), 0)

    # ---- 2026-11-03 起：劳动力市场整合因子 = 加拿大工作经验与 job offer 取较高者（上限 150）----
    job_offer_points = 0
    if regime == "new":
        regime_switch = scoring.get("regime_switch") or {}
        intent = profile.get("intent") or {}
        tier = str(intent.get("job_offer_wage_tier") or "none")
        job_offer_points = regime_switch.get("new_job_offer_points", {}).get(tier, 0)
        factor = min(max(cdn_work_points, job_offer_points), regime_switch.get("factor_cap", 150))
        unsupported.append("high-wage 加拿大工作经验加分（70/40/20 分档）——需 NOC 职业级工资数据，v0 未实现")
        cdn_work_points = factor
    core += cdn_work_points

    # ---- 配偶因子（max 40）----
    spouse_factors = 0
    if has_spouse:
        spouse_factors += scoring["spouse_factors"]["education"].get(_education_bucket(spouse.get("highest_degree")), 0)
        spouse_clb = clb_from_test(spouse.get("language") or {})
        spouse_factors += sum(_spouse_lang_points(scoring["spouse_factors"]["language_first"], spouse_clb[a]) for a in ABILITIES)
        spouse_cdn = 0.0
        if isinstance(spouse.get("years_in"), dict):
            spouse_cdn = spouse["years_in"].get("CA", 0.0)
        spouse_factors += scoring["spouse_factors"]["cdn_work_experience"].get(_cdn_work_bucket(spouse_cdn), 0)

    # ---- 技能转换 ----
    transfer = 0
    cond = _lang_condition(clb_eng if first_lang == "english" else {})
    foreign = work_block.get("years_related", 0.0) or 0.0
    foreign_bucket = _foreign_bucket(foreign)
    tr_row = _tr_edu_row(edu)

    if cond in ("one_under_9", "all_9_plus") and tr_row:
        transfer += scoring["transferability"]["edu_x_language"][tr_row][cond]
    if cdn_years >= 1 and tr_row:
        col = "two_plus_years" if cdn_years >= 2 else "one_year"
        transfer += scoring["transferability"]["edu_x_cdn_work"][tr_row][col]
    if foreign_bucket and cond in ("one_under_9", "all_9_plus"):
        transfer += scoring["transferability"]["foreign_work_x_language"][foreign_bucket][cond]
    if foreign_bucket and cdn_years >= 1:
        col = "two_plus_years" if cdn_years >= 2 else "one_year"
        transfer += scoring["transferability"]["foreign_work_x_cdn_work"][foreign_bucket][col]
    transfer = min(transfer, scoring["transferability"]["max_total"])

    # ---- 附加分（v0 未支持项，见 ee_crs.yaml meta.unsupported）----
    additional = 0
    unsupported += [
        "加拿大教育 15/30、兄弟姊妹 15、省份提名 600：画像 schema 无对应字段",
        "法语 NCLC 7+ 加分 25/50：对照表未入库",
    ]
    if regime == "current":
        unsupported.append("job offer 加分：现行规则值未获官方页确认；2026-11-03 起按新制计分（见 regime_switch）")

    return {
        "total": core + spouse_factors + transfer + additional,
        "sections": {
            "core": core,
            "spouse_factors": spouse_factors,
            "transferability": transfer,
            "additional": additional,
        },
        "unsupported": unsupported,
        "breakdown": {
            "age": {"years": age, "points": _age_points(scoring["age"][base], age)},
            "education": {"bucket": edu, "points": scoring["education"][base].get(edu, 0)},
            "first_language": {"clb": clb_eng if first_lang == "english" else None,
                               "points": sum(_first_lang_points(scoring["language_first"][base], clb_eng[a]) for a in ABILITIES) if first_lang == "english" else 0},
            "cdn_work_experience": {"years": cdn_years, "bucket": _cdn_work_bucket(cdn_years),
                                     "points": cdn_work_points, "regime": regime,
                                     "job_offer_points": job_offer_points if regime == "new" else None},
            "spouse_factors": spouse_factors,
            "transferability": transfer,
        },
        "regime": regime,
    }
