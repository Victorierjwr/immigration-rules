/* immigration-rules Web 比较器（local-first，无后端）
 * 引擎与规则经由 Pyodide 在浏览器内运行——与 CLI 完全同一份代码（单一事实源）。
 * 画像只存 localStorage，导出 JSON 供 CLI 复用。 */
"use strict";

const FILES = [
  "engine/__init__.py", "engine/profile_map.py", "engine/gates.py", "engine/gap.py", "engine/assess.py",
  "engine/calculators/__init__.py", "engine/calculators/canada_ee_crs.py",
  "engine/calculators/japan_hsp.py", "engine/calculators/germany_chancenkarte.py",
  "engine/tests/fixtures/sample_profile.json",
  "schema/profile-schema-v0.json",
  "rules/canada/ee_crs.yaml", "rules/canada/gates.yaml", "rules/canada/categories.yaml",
  "rules/canada/cutoff_history.csv", "rules/canada/process.yaml",
  "rules/japan/hsp_points.yaml", "rules/japan/process.yaml",
  "rules/germany/chancenkarte.yaml", "rules/germany/process.yaml",
  "rules/australia/pathways.yaml", "rules/australia/cutoff_history.csv", "rules/australia/process.yaml",
];
const REPO_FS = "/repo";
const STORAGE_KEY = "immigration-profile-v1";

const BASE = new URL("..", location).href;   // /web/index.html → 仓库根（Pages 与本地皆适用）
const $ = id => document.getElementById(id);
const setStatus = (msg, err) => { const el = $("status"); el.textContent = msg; el.classList.toggle("err", !!err); };

async function boot() {
  try {
    setStatus("加载 Pyodide 运行时…");
    const py = await loadPyodide();
    await py.loadPackage("micropip");
    const micropip = py.pyimport("micropip");
    setStatus("安装依赖（pyyaml / jsonschema）…");
    await micropip.install("pyyaml");
    let schemaMode = "完整";
    try { await micropip.install("jsonschema"); }
    catch { schemaMode = "轻量"; }

    setStatus(`载入引擎与规则（${FILES.length} 个文件）…`);
    py.FS.mkdirTree(REPO_FS);
    for (const rel of FILES) {
      const resp = await fetch(BASE + rel);
      if (!resp.ok) throw new Error(`fetch ${rel}: HTTP ${resp.status}`);
      const path = REPO_FS + "/" + rel;
      const dir = path.slice(0, path.lastIndexOf("/"));
      py.FS.mkdirTree(dir);
      py.FS.writeFile(path, await resp.text());
    }
    py.runPython(`import sys; sys.path.insert(0, "${REPO_FS}")`);
    window.__py = py;

    // 预热一次，把校验模式报给用户
    const warm = await py.runPythonAsync(
      "import json\n" +
      "from engine.assess import run_assessment\n" +
      `json.dumps(run_assessment(json.loads(r'''{"person":{}}'''))['mode'])`
    );
    setStatus(`就绪（${schemaMode} 校验 · 引擎已载入 ${FILES.length} 文件 · 规则版本随仓库更新）`);
    $("app").classList.remove("hide");
    $("run").onclick = runAssessment;
    $("save").onclick = saveProfile;
    $("export").onclick = exportProfile;
    $("clear").onclick = () => { localStorage.removeItem(STORAGE_KEY); location.reload(); };
    loadProfile();
  } catch (err) {
    setStatus("加载失败：" + err.message, true);
  }
}

/* ---------- 画像：表单 ↔ JSON ---------- */
function buildProfile() {
  const targets = [];
  if ($("t_ca").checked) targets.push("CA");
  if ($("t_jp").checked) targets.push("JP");
  if ($("t_de").checked) targets.push("DE");
  if ($("t_au").checked) targets.push("AU");
  const eng = $("f_eng_test").value;
  const profile = {
    person: {
      birth_date: $("f_birth").value || null,
      citizenship: $("f_cit").value ? [$("f_cit").value.trim().toUpperCase()] : [],
      marital_status: $("f_marital").value,
      children: Number($("f_children").value || 0),
    },
    education: {
      highest_degree: $("f_degree").value,
      country: $("f_edu_country").value.trim().toUpperCase() || "CN",
      completed_date: $("f_edu_date").value || null,
      eca_done: $("f_eca").value === "true",
    },
    language: {
      english: {
        test: eng,
        overall: eng === "none" ? null : Number($("f_l").value || 0),
        listening: eng === "none" ? null : Number($("f_l").value || 0),
        reading: eng === "none" ? null : Number($("f_r").value || 0),
        writing: eng === "none" ? null : Number($("f_w").value || 0),
        speaking: eng === "none" ? null : Number($("f_s").value || 0),
      },
      other: { german: $("f_ger").value || null },
    },
    work: {
      occupation_title: $("f_occ").value || "unspecified",
      years_total: Number($("f_years_t").value || 0),
      years_related: Number($("f_years_r").value || 0),
      years_in: { CA: Number($("f_yca").value || 0), DE: Number($("f_yde").value || 0) },
      high_wage_tier_CA: $("f_hw").value,
      income_annual: { amount: Number($("f_income").value || 0), currency: $("f_cur").value },
    },
    intent: {
      target_countries: targets,
      job_offer_wage_tier: $("f_offer").value,
      budget: $("f_budget").value ? { max_total: { amount: Number($("f_budget").value), currency: "EUR" } } : undefined,
    },
  };
  if (!profile.intent.budget) delete profile.intent.budget;
  const pasted = $("json_in").value.trim();
  if (pasted) {
    try { return JSON.parse(pasted); }
    catch { return profile; }   // JSON 语法错时退回表单
  }
  return profile;
}

function fillForm(profile) {
  const p = profile.person || {}, e = profile.education || {}, l = profile.language || {}, w = profile.work || {}, i = profile.intent || {};
  if (p.birth_date) $("f_birth").value = p.birth_date;
  if (p.citizenship && p.citizenship[0]) $("f_cit").value = p.citizenship[0];
  if (p.marital_status) $("f_marital").value = p.marital_status;
  if (p.children !== undefined) $("f_children").value = p.children;
  if (e.highest_degree) $("f_degree").value = e.highest_degree;
  if (e.country) $("f_edu_country").value = e.country;
  if (e.completed_date) $("f_edu_date").value = e.completed_date;
  if (e.eca_done !== undefined) $("f_eca").value = String(e.eca_done);
  if (l.english) {
    $("f_eng_test").value = l.english.test || "none";
    if (l.english.listening !== null && l.english.listening !== undefined) $("f_l").value = l.english.listening;
    if (l.english.reading !== null && l.english.reading !== undefined) $("f_r").value = l.english.reading;
    if (l.english.writing !== null && l.english.writing !== undefined) $("f_w").value = l.english.writing;
    if (l.english.speaking !== null && l.english.speaking !== undefined) $("f_s").value = l.english.speaking;
  }
  if (l.other && l.other.german) $("f_ger").value = l.other.german;
  if (w.occupation_title) $("f_occ").value = w.occupation_title;
  if (w.years_total !== undefined) $("f_years_t").value = w.years_total;
  if (w.years_related !== undefined) $("f_years_r").value = w.years_related;
  if (w.years_in) { if (w.years_in.CA !== undefined) $("f_yca").value = w.years_in.CA; if (w.years_in.DE !== undefined) $("f_yde").value = w.years_in.DE; }
  if (w.high_wage_tier_CA) $("f_hw").value = w.high_wage_tier_CA;
  if (w.income_annual) { $("f_income").value = w.income_annual.amount; $("f_cur").value = w.income_annual.currency; }
  if (i.job_offer_wage_tier) $("f_offer").value = i.job_offer_wage_tier;
  if (i.budget && i.budget.max_total) $("f_budget").value = i.budget.max_total.amount;
  (i.target_countries || []).forEach(c => {
    const box = { CA: "t_ca", JP: "t_jp", DE: "t_de", AU: "t_au" }[c];
    if (box) $(box).checked = true;
  });
}

async function runAssessment() {
  const btn = $("run");
  btn.disabled = true;
  $("report").textContent = "计算中（浏览器内本地执行）…";
  try {
    const profile = buildProfile();
    const asOf = $("f_asof").value || null;
    const payload = JSON.stringify({ profile, as_of: asOf, lang: $("f_lang").value });
    const py = window.__py;
    py.globals.set("_profile_payload", payload);   // 先设全局，再执行
    const out = await py.runPythonAsync(
      "import json\n" +
      "from engine.assess import run_assessment\n" +
      "_input = json.loads(_profile_payload)\n" +
      "_result = run_assessment(_input['profile'], as_of=_input.get('as_of'), lang=_input.get('lang', 'zh'))\n" +
      "json.dumps(_result, ensure_ascii=False)"
    );
    const result = JSON.parse(out);
    $("report").textContent = result.ok
      ? result.markdown
      : "画像未通过校验（" + result.mode + "）：\n" + result.errors.map(e => "  - " + e).join("\n");
    localStorage.setItem(STORAGE_KEY, JSON.stringify(profile));
  } catch (err) {
    $("report").textContent = "运行失败：" + err.message;
  } finally {
    btn.disabled = false;
  }
}

function saveProfile() { localStorage.setItem(STORAGE_KEY, JSON.stringify(buildProfile())); setStatus("画像已保存到本机（localStorage）"); }
function exportProfile() {
  const blob = new Blob([JSON.stringify(buildProfile(), null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "profile.json";
  a.click();
}
function loadProfile() {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved) { try { fillForm(JSON.parse(saved)); } catch {} }
  $("f_asof").value = new Date().toISOString().slice(0, 10);
}

boot();
