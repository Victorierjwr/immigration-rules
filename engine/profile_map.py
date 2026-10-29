"""派生特征层：canonical 画像 → 国别计算所需派生特征。

映射规则即测试规则：profile_map_test 覆盖所有换算边界。
派生字段供 gates 表达式与计算器读取，不代表任何政策断言——换算表以官方为准。
"""
from __future__ import annotations

from datetime import date, datetime

# IELTS General Training → CLB（每项能力，向下取整；官方语言测试对照表）
# 来源：canada.ca 语言测试对照（CLB 10 起四能力封顶）
IELTS_TO_CLB = {
    "listening": [(8.5, 10), (8.0, 9), (7.5, 8), (6.0, 7), (5.5, 6), (5.0, 5), (4.5, 4), (4.0, 3)],
    "reading":   [(8.0, 10), (7.0, 9), (6.5, 8), (6.0, 7), (5.0, 6), (4.0, 5), (3.5, 4)],
    "writing":   [(7.5, 10), (7.0, 9), (6.5, 8), (6.0, 7), (5.5, 6), (5.0, 5), (4.0, 4)],
    "speaking":  [(7.5, 10), (7.0, 9), (6.5, 8), (6.0, 7), (5.5, 6), (5.0, 5), (4.0, 4)],
}

# CELPIP-G → CLB：4-9 区间分数即 CLB；≥10 折算为 CLB 10+（CRS 取点封顶 CLB 10）
CELPIP_CAP = 10

ABILITIES = ("listening", "reading", "writing", "speaking")


def _band_to_clb(score: float | None, table: list[tuple[float, int]]) -> int | None:
    if score is None:
        return None
    for band, clb in table:
        if score >= band:
            return clb
    return 0


def age_years(profile: dict, today: date | None = None) -> int:
    """满周岁（非年差）——生日边界不再差一岁。"""
    birth = profile.get("person", {}).get("birth_date")
    if not birth:
        return 0
    today = today or date.today()
    b = date.fromisoformat(str(birth))
    return max(0, today.year - b.year - ((today.month, today.day) < (b.month, b.day)))


def clb_from_test(test: dict) -> dict:
    """{overall, listening, ...} → 各能力 CLB（英语系测试）。"""
    result: dict[str, int | None] = {}
    if test.get("test") == "none":
        result.update({a: None for a in ABILITIES})
        return result
    if test.get("test") == "ielts":
        for a in ABILITIES:
            result[a] = _band_to_clb(test.get(a), IELTS_TO_CLB[a])
    elif test.get("test") == "celpip":
        for a in ABILITIES:
            v = test.get(a)
            result[a] = None if v is None else min(int(v), CELPIP_CAP)
    else:
        # TOEFL/PTE 的官方对照表未在 v0 入库；不猜测，留 None
        result.update({a: None for a in ABILITIES})
    return result


def derived(profile: dict, countries: list[str] | None = None) -> dict:
    """构建派生特征字典：供 gates 表达式与计算器消费。"""
    counts = countries or ["CA", "JP", "DE", "AU"]
    out = {"age_years": age_years(profile)}

    eng = (profile.get("language") or {}).get("english") or {}
    clb = clb_from_test(eng)
    clb_vals = [v for v in clb.values() if v is not None]
    out["clb_english"] = clb
    out["clb_english_min"] = min(clb_vals) if clb_vals else None

    if "CA" in counts:
        work = profile.get("work") or {}
        out["years_in_CA"] = (work.get("years_in") or {}).get("CA", 0.0)
        spouse = (profile.get("person") or {}).get("spouse_profile") or {}
        out["spouse_years_in_CA"] = float((spouse.get("years_in") or {}).get("CA", 0.0))
        out["spouse_education"] = spouse.get("highest_degree")
        spouse_lang = (spouse.get("language") or {}).get("test", "none")
        out["spouse_language_test"] = spouse_lang

    return out


def french_nclc_unsupported() -> str:
    return "TEF/TCF Canada → NCLC 官方对照表未入库，v0 不做法语 NCLC 自动换算"


def str_keys(node):
    """YAML 整数键（如 2: 53）与字符串键并存易出 bug——统一转字符串键。"""
    if isinstance(node, dict):
        return {str(k): str_keys(v) for k, v in node.items()}
    if isinstance(node, list):
        return [str_keys(v) for v in node]
    return node
