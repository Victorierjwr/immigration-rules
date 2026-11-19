# Web 比较器使用说明（local-first PWA）

无后端、画像不出浏览器。引擎与规则经 Pyodide 在浏览器内运行——与 CLI 是同一份 Python 代码（单一事实源，不存在 JS 移植的漂移问题）。

## 两种打开方式

**1. 本地（开发/自用）**

```bash
cd F:\Development\skillsproject\immigration-rules
python -m http.server 8000
# 浏览器打开 http://localhost:8000/web/
```

**2. GitHub Pages（公开给所有人）**

仓库 → Settings → Pages → Deploy from a branch → 选 `main` / `(root)` → Save。
发布后地址：`https://victorierjwr.github.io/immigration-rules/web/`

## 特性

- 首次访问后**离线可用**（Service Worker 缓存引擎、规则与本页）
- 画像只存 localStorage（保存/导出 JSON/粘贴导入）；导出的 JSON 可直接喂 CLI：`python -m engine.assess profile.json`
- 报告语言 zh/en/ja；评估基准日可指定（CRS 双制切换）
- 校验：浏览器内 Pyodide 安装完整 jsonschema（实测可行）；安装失败自动降级为轻量校验（必需字段检查）

## 实现说明

- `web/app.js`：把 `engine/` + `rules/` + `schema/` 共 23 个文件写入 Pyodide 虚拟文件系统 `/repo`，`import engine.assess` 后调用 `run_assessment()`——与 CLI/MCP 完全同源
- PWA：manifest + Service Worker（cache-first，仅同源资源）
- 无头验证：Node + pyodide 包跑同一流程已验证（四国矩阵 + 错误路径）
