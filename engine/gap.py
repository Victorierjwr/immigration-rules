"""邀请轮动态 gap 分析器：分数对照官方 cutoff 历史。

纪律：该类别本年度无邀请记录 → 输出 CATEGORY_NO_DRAWS，绝不编造 cutoff。
数据源：rules/<country>/cutoff_history.csv（每行带 source_url）。
输出双参考：类别轮（现有逻辑）+ 全项目/项目轮参考——FSW/CEC 申请人真实竞争的是项目轮。
"""
from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_cutoffs(path: Path) -> list[dict]:
    rows = []
    if not path.exists():
        return rows
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if not (row.get("draw_date") or "").strip():
                continue
            cutoff = float(row["cutoff"].replace(",", "")) if (row.get("cutoff") or "").strip() else None
            invitations = int(row["invitations"].replace(",", "")) if (row.get("invitations") or "").strip() else None
            rows.append({
                "draw_date": row["draw_date"],
                "round_type": row["round_type"],
                "category": (row.get("category") or "").strip() or None,
                "invitations": invitations,
                "cutoff": cutoff,
                "source_url": row.get("source_url") or "",
            })
    return rows


def _recent(rows: list[dict], months: int) -> list[dict]:
    if not rows:
        return []
    cutoff_date = date.fromisoformat(sorted(rows, key=lambda r: r["draw_date"])[-1]["draw_date"])
    start = cutoff_date - timedelta(days=365 * months)
    return [r for r in rows if date.fromisoformat(r["draw_date"]) >= start]


def _latest_ref(rows: list[dict]) -> dict | None:
    if not rows:
        return None
    latest = sorted(rows, key=lambda r: r["draw_date"], reverse=True)[0]
    cutoffs = [r["cutoff"] for r in rows if r["cutoff"] is not None]
    median = float(sorted(cutoffs)[len(cutoffs) // 2]) if cutoffs else None
    return {
        "latest_draw": latest,
        "cutoff": latest["cutoff"],
        "median_12mo": median,
        "draws_in_window": len(rows),
        "source_url": latest["source_url"],
    }


def analyze(score: int | float, country: str, rows: list[dict] | None = None,
            category: str | None = None, months: int = 12) -> dict:
    if rows is None:
        rows = load_cutoffs(ROOT / "rules" / country / "cutoff_history.csv")

    # 类别轮参考
    cat_rows = [r for r in rows if r["round_type"] == "category" and r.get("category")]
    if category:
        cat_rows = [r for r in cat_rows if r["category"] == category]
    cat_ref = _latest_ref(_recent(cat_rows, months))
    if cat_ref:
        cat_ref["status"] = "OK"
        cat_ref["gap"] = score - cat_ref["cutoff"] if cat_ref["cutoff"] is not None else None
    else:
        cat_ref = {"status": "CATEGORY_NO_DRAWS",
                   "message": f"近 {months} 个月内该类别/通路无邀请轮记录——不估分；请关注官方轮次页"}

    # 全项目/项目轮参考（FSW/CEC 真实竞争池）
    prog_ref = _latest_ref(_recent([r for r in rows if r["round_type"] in ("general", "program")], months))
    if prog_ref:
        prog_ref["status"] = "OK"
        prog_ref["gap"] = score - prog_ref["cutoff"] if prog_ref["cutoff"] is not None else None

    result = {"category": cat_ref}
    if prog_ref:
        result["general"] = prog_ref
    return result
