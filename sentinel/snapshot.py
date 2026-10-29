#!/usr/bin/env python3
"""Sentinel snapshot：定时抓取官方公开页 → 归一化文本 → git 快照存档 → diff → 待审 Issue。

纪律（GOVERNANCE.md / 实施规划）：
- 只读官方公开页；失败重试；连续失败达 targets.defaults.staleness_alert_days 自动开 alert Issue
- diff 只产出待审 Issue（sentinel/pending/），规则变更永远走人工 PR，绝不自动改规则
- 快照与 state.json 由 workflow 提交进 git，git 即存档

用法：
  python sentinel/snapshot.py             # 正常运行；CI 内（GH_TOKEN+gh 存在）自动建/评 Issue
  python sentinel/snapshot.py --dry-run   # 只检测与打印，不写任何文件
"""
import argparse
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

import requests
import yaml
from bs4 import BeautifulSoup

HERE = Path(__file__).resolve().parent
SNAPSHOTS = HERE / "snapshots"
PENDING = HERE / "pending"
STATE_FILE = HERE / "state.json"
TARGETS_FILE = HERE / "targets.yaml"

MAX_DIFF_LINES = 400
ISSUE_LABELS = [
    ("sentinel-change", "D93F0B", "sentinel detected an official page change"),
    ("needs-review", "0E8A16", "awaiting human triage"),
    ("sentinel-alert", "B60205", "sentinel fetch degraded/failing"),
    ("confirmed", "1D76DB", "triaged; ready to publish"),
    ("published", "C2E0C6", "changelog/RSS/telegram done"),
    ("false-positive", "FBCA04", "template/nav change, no policy meaning"),
]

SESSION = requests.Session()
SESSION.headers.update(
    {"User-Agent": "immigration-rules-sentinel/0.1 (open-source rules-as-code monitor)"}
)


def log(msg: str) -> None:
    print(msg, flush=True)


def load_targets() -> tuple[dict, list[dict]]:
    raw = yaml.safe_load(TARGETS_FILE.read_text(encoding="utf-8"))
    return raw.get("defaults") or {}, raw.get("targets") or []


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"schema_version": 0, "targets": {}}


def save_state(state: dict) -> None:
    state["last_run"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def is_due(target: dict, today: date) -> tuple[bool, str]:
    freq = target.get("frequency", "daily")
    if freq == "daily":
        return True, ""
    if freq == "weekly":
        if today.weekday() == 6:  # Sunday
            return True, ""
        return False, "weekly 目标仅在周日快照"
    if freq == "manual":
        return False, "manual 目标：JS 渲染页无法纯 HTTP 抓取，按调整规则 3 每周人工核对"
    return False, f"未知 frequency: {freq}"


def fetch(url: str, tries: int = 3) -> tuple[str | None, str | None]:
    err = None
    for attempt in range(tries):
        try:
            resp = SESSION.get(url, timeout=30)
            if resp.status_code == 200 and resp.text.strip():
                # 多数政府站响应头不带 charset，requests 会按 ISO-8859-1 误解码（如 moj.go.jp）
                if "charset" not in resp.headers.get("Content-Type", "").lower():
                    resp.encoding = resp.apparent_encoding
                return resp.text, None
            err = f"HTTP {resp.status_code}"
        except requests.RequestException as exc:
            err = f"{type(exc).__name__}: {exc}"[:200]
        if attempt < tries - 1:
            time.sleep(3 * (attempt + 1))
    return None, err


NOISE_TAGS = ["script", "style", "noscript", "svg", "iframe", "form", "nav", "header", "footer"]


def normalize(html: str, selector: str | None) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag_name in NOISE_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()
    node = soup.select_one(selector) if selector else (soup.body or soup)
    text = node.get_text("\n") if node else ""
    lines = []
    for line in text.splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def keyword_hits(diff_lines: list[str], keywords: list[str]) -> list[str]:
    joined = "\n".join(diff_lines).lower()
    return [k for k in keywords if k.lower() in joined]


def render_issue_body(target: dict, diff_text: str, added: int, removed: int, hits: list[str], now: str) -> str:
    kw = "、".join(hits) if hits else "无（可能是模板/导航改版）"
    diff_block = "\n".join(diff_text.splitlines()[:MAX_DIFF_LINES])
    if len(diff_text.splitlines()) > MAX_DIFF_LINES:
        diff_block += f"\n…（截断，完整 diff 见 {SNAPSHOTS.name}/ 快照对比）"
    return f"""## 变更摘要（人工填写 → 加 `confirmed` 标签发布）

### 变了什么
<!-- 1-3 句，只写官方页面事实，不推测影响。写法见 sentinel/summarizer.md -->

### 对谁有影响
<!-- 哪类申请人 / 哪条通路；若无政策含义（模板改版）→ 加 false-positive 标签并关闭 -->

### 官方链接
- {target["url"]}

## 检测详情（自动生成）
- 目标: `{target["id"]}` ({target["country"]})
- 检测时间: {now}
- 与上一快照差异: +{added} / -{removed} 行
- 关键词命中: {kw}

<details><summary>Diff（前 {MAX_DIFF_LINES} 行）</summary>

```diff
{diff_block}
```
</details>

> 流程：snapshot 自动开 Issue → maintainer 按 summarizer.md 填摘要 → 加 `confirmed` → publish workflow 自动写 changelog/RSS/Telegram 并关闭本 Issue。
> 规则数据如需变更：另行提 PR（见 CONTRIBUTING.md），本 Issue 不承载规则修改。
"""


def render_alert_body(target: dict, failures: int, last_error: str | None, now: str) -> str:
    return f"""## 抓取连续失败告警（自动生成）

- 目标: `{target["id"]}` ({target["country"]})
- 连续失败/降级: {failures} 天（达 targets.defaults.staleness_alert_days 阈值）
- 最近错误: {last_error or "n/a"}
- 检测时间: {now}

处理选项：人工打开页面确认 URL 是否迁移 → 修 targets.yaml 并 PR；或确认站点临时故障 → 本 Issue 留言后关闭，计数下轮成功时归零。
"""


def gh_ready() -> bool:
    return bool(shutil.which("gh") and os.environ.get("GH_TOKEN") and os.environ.get("GITHUB_REPOSITORY"))


def gh(args: list[str], input_text: str | None = None) -> tuple[bool, str]:
    proc = subprocess.run(
        ["gh", *args], capture_output=True, text=True,
        input=input_text, encoding="utf-8", errors="replace",
    )
    return proc.returncode == 0, (proc.stdout or "") + (proc.stderr or "")


def ensure_labels() -> None:
    for name, color, desc in ISSUE_LABELS:
        gh(["label", "create", name, "--color", color, "--description", desc, "--force"])


def find_open_issue(target_id: str) -> int | None:
    ok, out = gh(["issue", "list", "--label", "sentinel-change", "--state", "open", "--json", "number,title"])
    if not ok:
        return None
    try:
        issues = json.loads(out)
    except json.JSONDecodeError:
        return None
    for item in issues:
        if target_id in item.get("title", ""):
            return int(item["number"])
    return None


def deliver_issue(target: dict, body: str, title: str, labels: list[str], state: dict, dry_run: bool) -> None:
    PENDING.mkdir(parents=True, exist_ok=True)
    pending_file = PENDING / f"{target['id']}-{date.today().isoformat()}.md"
    pending_file.write_text(body, encoding="utf-8")
    if dry_run:
        log(f"    [dry-run] 待审 Issue 草稿已生成: {pending_file.name}")
        return
    if not gh_ready():
        log(f"    gh 不可用：Issue 草稿保留在 {pending_file}（推送到 GitHub 后由 workflow 自动提交）")
        return
    ensure_labels()
    repo = os.environ["GITHUB_REPOSITORY"]
    open_issue = find_open_issue(target["id"])
    if open_issue:
        ok, out = gh(["issue", "comment", str(open_issue), "--body-file", str(pending_file)])
        if ok:
            pending_file.unlink(missing_ok=True)
            log(f"    已追加评论到既有 Issue #{open_issue}")
        else:
            log(f"    gh 评论失败: {out.strip()[:200]}")
        return
    ok, out = gh(["issue", "create", "--title", title, "--body-file", str(pending_file), "--label", ",".join(labels)])
    if ok:
        pending_file.unlink(missing_ok=True)
        match = re.search(r"/issues/(\d+)", out)
        if match:
            state["targets"].setdefault(target["id"], {})["open_issue"] = int(match.group(1))
        log(f"    已创建 Issue: {out.strip().splitlines()[-1] if out.strip() else '?'}")
    else:
        log(f"    gh 建档失败: {out.strip()[:200]}（草稿保留在 {pending_file}）")


def process(target: dict, defaults: dict, state: dict, dry_run: bool, today: date) -> None:
    tid = target["id"]
    tstate = state["targets"].setdefault(tid, {})
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    html, err = fetch(target["url"])
    if html is None:
        tstate["consecutive_failures"] = int(tstate.get("consecutive_failures", 0)) + 1
        tstate["last_error"] = err
        tstate["last_checked"] = now
        failures = tstate["consecutive_failures"]
        log(f"  FAIL {tid}: {err}（连续第 {failures} 次）")
        alert_after = int(defaults.get("staleness_alert_days", 14))
        if failures == alert_after:
            deliver_issue(
                target, render_alert_body(target, failures, err, now),
                f"[sentinel][alert] {target['country']} {tid} 连续 {failures} 天抓取失败",
                ["sentinel-alert"], state, dry_run,
            )
        return

    text = normalize(html, target.get("selector"))
    tstate["last_checked"] = now
    tstate["content_chars"] = len(text)

    min_chars = int(defaults.get("min_content_chars", 500))
    if len(text) < min_chars:
        tstate["consecutive_failures"] = int(tstate.get("consecutive_failures", 0)) + 1
        tstate["degraded"] = True
        tstate["last_error"] = f"normalized content too small: {len(text)} chars（JS 渲染或页面结构变化）"
        failures = tstate["consecutive_failures"]
        log(f"  DEGRADED {tid}: 文本量 {len(text)} < {min_chars}（连续第 {failures} 次）")
        alert_after = int(defaults.get("staleness_alert_days", 14))
        if failures == alert_after:
            deliver_issue(
                target, render_alert_body(target, failures, tstate["last_error"], now),
                f"[sentinel][alert] {target['country']} {tid} 内容量异常 {failures} 天",
                ["sentinel-alert"], state, dry_run,
            )
        return

    tstate["consecutive_failures"] = 0
    tstate["degraded"] = False
    new_hash = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()

    prev_hash = tstate.get("last_hash")
    if prev_hash == new_hash:
        # 状态哈希匹配但快照文件可能丢失（手工删除/换库）→ 按状态重建
        snapshot_dir = SNAPSHOTS / tid
        prev_files = sorted(snapshot_dir.glob("*.txt")) if snapshot_dir.exists() else []
        if not prev_files and not dry_run:
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            snapshot_path = snapshot_dir / f"{today.isoformat()}.txt"
            snapshot_path.write_text(text, encoding="utf-8")
            tstate["last_snapshot"] = str(snapshot_path.relative_to(HERE.parent))
            log(f"  rebuilt {tid}: 快照文件缺失，按状态哈希重建")
        else:
            log(f"  unchanged {tid}")
        return

    snapshot_dir = SNAPSHOTS / tid
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = snapshot_dir / f"{today.isoformat()}.txt"

    diff_text = ""
    added = removed = 0
    hits: list[str] = []
    if prev_hash and snapshot_dir.exists():
        prev_files = sorted(snapshot_dir.glob("*.txt"))
        prev_text = prev_files[-1].read_text(encoding="utf-8") if prev_files else ""
        if prev_text and prev_text != text:
            diff_lines = list(difflib.unified_diff(
                prev_text.splitlines(), text.splitlines(),
                fromfile="previous", tofile="current", lineterm="",
            ))
            diff_text = "\n".join(diff_lines)
            added = sum(1 for ln in diff_lines if ln.startswith("+") and not ln.startswith("+++"))
            removed = sum(1 for ln in diff_lines if ln.startswith("-") and not ln.startswith("---"))
            hits = keyword_hits([ln for ln in diff_lines if ln[:1] in "+-"], target.get("keywords") or [])
            log(f"  CHANGED {tid}: +{added}/-{removed}，关键词命中: {hits or '无'}")

    if not dry_run:
        snapshot_path.write_text(text, encoding="utf-8")
    tstate["last_hash"] = new_hash
    tstate["last_snapshot"] = str(snapshot_path.relative_to(HERE.parent))

    if diff_text:
        body = render_issue_body(target, diff_text, added, removed, hits, now)
        title = f"[sentinel] {target['country']} {tid} 页面变更 {today.isoformat()}"
        deliver_issue(target, body, title, ["sentinel-change", "needs-review"], state, dry_run)
    else:
        log(f"  baseline {tid}: 首次快照已存档（{len(text)} 字符）")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="只检测与打印，不写快照/状态/Issue")
    args = parser.parse_args()

    defaults, targets = load_targets()
    state = load_state()
    today = datetime.now(timezone.utc).date()
    log(f"sentinel snapshot @ {datetime.now(timezone.utc).isoformat(timespec='seconds')}（{len(targets)} 个目标）")

    for target in targets:
        due, reason = is_due(target, today)
        if not due:
            log(f"  skip {target['id']}: {reason}")
            continue
        log(f"  check {target['id']} → {target['url']}")
        process(target, defaults, state, args.dry_run, today)

    if not args.dry_run:
        save_state(state)
        log("state.json 已更新")
    return 0


if __name__ == "__main__":
    sys.exit(main())
