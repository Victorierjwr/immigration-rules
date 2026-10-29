#!/usr/bin/env python3
"""Publish 确认后的变更：changelog.jsonl → changelog.md + feed.xml + Telegram。

触发链：maintainer 在 sentinel Issue 上加 confirmed 标签 → publish workflow → 本脚本。
输入：Issue body（workflow 用 gh 导出为文件，--body-file 传入）+ 环境变量。

Issue body 中解析的段落由 summarizer.md 模板约定：
  ### 变了什么 / ### 对谁有影响 / ### 官方链接 / 检测详情里的 目标: `<id>`

Telegram：TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID 存在才发送，缺失则跳过（不影响 changelog/RSS）。
"""
import argparse
import html
import json
import os
import re
import xml.sax.saxutils as xmlutils
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path

import requests
import yaml

HERE = Path(__file__).resolve().parent
DOCS = HERE.parent / "docs"
TARGETS_FILE = HERE / "targets.yaml"
CHANGELOG_MD = DOCS / "changelog.md"
CHANGELOG_JSONL = DOCS / "changelog.jsonl"
FEED_XML = DOCS / "feed.xml"

HEADER_MD = """# 政策变更 changelog

> 由 sentinel 自动维护：检测 Issue 经 maintainer 填摘要、加 `confirmed` 标签后自动追加。
> RSS 订阅：仓库内 `docs/feed.xml`（启用 GitHub Pages 后可通过 Pages 链接订阅）。
> 免责：本页为官方公开信息的变更记录，不构成移民建议。

<!-- 本文件由 sentinel/publish.py 全量再生成，请勿手工编辑；内容修改请改对应 Issue 后重新发布 -->
"""


def log(msg: str) -> None:
    print(msg, flush=True)


def section(body: str, start: str, end: str | None) -> str:
    idx = body.find(start)
    if idx < 0:
        return ""
    body = body[idx + len(start):]
    if end:
        stop = body.find(end)
        if stop >= 0:
            body = body[:stop]
    text = body.strip()
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    return text.strip()


def first_url(text: str) -> str:
    match = re.search(r"https?://\S+", text)
    return match.group(0).rstrip(").>,") if match else ""


def parse_issue(body: str) -> dict:
    what = section(body, "### 变了什么", "### 对谁有影响")
    who = section(body, "### 对谁有影响", "### 官方链接")
    link_section = section(body, "### 官方链接", "## 检测详情")
    target_match = re.search(r"目标:\s*`?([\w-]+)`?", body)
    return {
        "what": what or "(维护者未填写摘要——发布前应填写)",
        "who": who or "",
        "url": first_url(link_section),
        "target_id": target_match.group(1) if target_match else "",
    }


def load_target(target_id: str) -> dict:
    raw = yaml.safe_load(TARGETS_FILE.read_text(encoding="utf-8"))
    for target in raw.get("targets", []):
        if target["id"] == target_id:
            return target
    return {"id": target_id, "country": "unknown", "name": target_id}


def append_entry(entry: dict) -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    with CHANGELOG_JSONL.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_entries() -> list[dict]:
    if not CHANGELOG_JSONL.exists():
        return []
    return [json.loads(line) for line in CHANGELOG_JSONL.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_changelog_md(entries: list[dict]) -> None:
    parts = [HEADER_MD]
    for entry in sorted(entries, key=lambda e: e["date"], reverse=True):
        parts.append(f"## {entry['date']} · {entry['country']} · {entry['target_name']}\n")
        parts.append(f"**变了什么**：{entry['what']}\n")
        if entry.get("who"):
            parts.append(f"**对谁有影响**：{entry['who']}\n")
        source = f"[官方页面]({entry['url']})" if entry.get("url") else "（无链接）"
        issue = f" · 检测 Issue #{entry['issue_number']}" if entry.get("issue_number") else ""
        parts.append(f"{source}{issue}\n")
    CHANGELOG_MD.write_text("\n".join(parts), encoding="utf-8")


def write_feed(entries: list[dict]) -> None:
    repo_url = os.environ.get("REPO_URL", "https://github.com/immigration-rules/immigration-rules")
    items = []
    for entry in sorted(entries, key=lambda e: (e["date"], e.get("published_at", "")), reverse=True)[:50]:
        dt = datetime.fromisoformat(entry["published_at"]) if entry.get("published_at") else datetime.fromisoformat(entry["date"] + "T00:00:00+00:00")
        title = f"{entry['country']}: {entry['what'][:100]}"
        link = entry.get("issue_url") or repo_url
        desc = entry["what"] + (f" ｜ 影响：{entry['who']}" if entry.get("who") else "")
        items.append(
            "<item>"
            f"<title>{xmlutils.escape(title)}</title>"
            f"<link>{xmlutils.escape(link)}</link>"
            f"<guid>{xmlutils.escape(link + '#' + entry['date'] + '-' + entry['target_id'])}</guid>"
            f"<pubDate>{format_datetime(dt)}</pubDate>"
            f"<description>{xmlutils.escape(desc)}</description>"
            "</item>"
        )
    feed = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0"><channel>'
        f"<title>immigration-rules 政策变更哨兵</title>"
        f"<link>{xmlutils.escape(repo_url)}</link>"
        "<description>官方移民政策页面变更记录（加拿大/澳洲/日本/德国）——开源、带官方溯源</description>"
        "<language>zh-CN</language>"
        + "".join(items) +
        "</channel></rss>\n"
    )
    FEED_XML.write_text(feed, encoding="utf-8")


def send_telegram(entry: dict) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        log("telegram: secrets 未配置，跳过推送")
        return
    lines = [
        f"🛰 <b>{html.escape(entry['country'].upper())} · {html.escape(entry['target_name'])}</b>",
        html.escape(entry["what"]),
    ]
    if entry.get("who"):
        lines.append(html.escape("影响：" + entry["who"]))
    if entry.get("url"):
        lines.append(f'来源: <a href="{html.escape(entry["url"])}">官方页面</a>')
    if entry.get("issue_url"):
        lines.append(f'<a href="{html.escape(entry["issue_url"])}">检测详情</a>')
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": "\n".join(lines), "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=20,
        )
        log(f"telegram: HTTP {resp.status_code}")
    except requests.RequestException as exc:
        log(f"telegram: 发送失败 {type(exc).__name__}: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--body-file", required=True, help="Issue body 文件（workflow 由 gh 导出）")
    args = parser.parse_args()

    issue_number = int(os.environ.get("ISSUE_NUMBER", "0"))
    issue_url = ""
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if repo and issue_number:
        issue_url = f"https://github.com/{repo}/issues/{issue_number}"

    body = Path(args.body_file).read_text(encoding="utf-8")
    parsed = parse_issue(body)
    target = load_target(parsed["target_id"])
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    entry = {
        "date": now[:10],
        "published_at": now,
        "country": target.get("country", "unknown"),
        "target_id": target.get("id", parsed["target_id"]),
        "target_name": target.get("name", parsed["target_id"]),
        "what": parsed["what"],
        "who": parsed["who"],
        "url": parsed["url"] or target.get("url", ""),
        "issue_number": issue_number or None,
        "issue_url": issue_url or None,
    }

    append_entry(entry)
    entries = read_entries()
    write_changelog_md(entries)
    write_feed(entries)
    log(f"changelog: {len(entries)} 条，已再生成 changelog.md 与 feed.xml")

    send_telegram(entry)
    return 0


if __name__ == "__main__":
    main()
