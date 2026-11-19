# Submission to the OECD Consultation: "Towards a Shared Reference Framework for Law as Code"

**From:** immigration-rules — an open-source, community-maintained Rules-as-Code project for cross-border immigration assessment
**License:** Data CC BY 4.0 · Code Apache-2.0
**Repository:** https://github.com/Victorierjwr/immigration-rules
**Date:** 2026-11-20
**Status:** draft for submission before the consultation closes (April 2027)

---

## 1. What we built

immigration-rules is a working, vertical Rules-as-Code implementation covering skilled-migration pathways in four jurisdictions (Canada Express Entry CRS, Japan Highly Skilled Professional points, Germany Chancenkarte, and an information layer for Australia). It is small enough to be fully inspectable and production enough to serve real users through three delivery channels from one rules base: a command-line tool, an Agent Skill (the cross-vendor SKILL.md format), and a browser application that runs the same Python engine in-browser via Pyodide.

We submit our methodology and lessons for the framework's consideration, offering the repository as a reference implementation that framework authors may reuse, critique, or cite.

## 2. Methodology contributions

**2.1 Provenance as CI-enforced metadata.** Every rule file carries three mandatory fields — `source_url` (official domain only), `effective_date`, and `last_verified` — plus the identity of the human verifier. CI rejects any file lacking them and blocks rules not verified for more than 180 days. Provenance here is not documentation; it is a build gate.

**2.2 Gates before scores.** Real eligibility is *gates → scoring → gap*: a set of hard disqualifiers (language floors, credential recognition, minimum income) evaluated before any arithmetic. Encoding gates as declarative, separately tested expressions mirrors the legal structure better than a single scoring function, and produces explainable refusal reasons with official links instead of unexplained numbers.

**2.3 Official worked examples as the highest arbiter.** Every pathway ships golden tests derived from official worked examples and boundary cases (exact age thresholds, exact score lines). Rule changes cannot merge unless all golden tests pass. Twice during development the hand-derived expectations were wrong and the implementation right — independent derivation of expected values is itself a quality mechanism worth standardising.

**2.4 Automation proposes, humans decide.** A sentinel diffs official pages on a schedule, drafts structured change summaries, and files issues; rules change only through human-reviewed pull requests requiring official citations and co-signature by two maintainers. In three weeks of production the sentinel caught a genuine mid-cycle policy correction (category eligibility, 2026-11-17) that page announcements alone would have missed — and taught us to monitor the page that carries the rules, not the page that announces them.

**2.5 Confidence marking at the presentation layer.** Every conclusion shown to users carries a visible confidence tier: ● verified (golden-covered, fresh), ◐ traced (official source, no regression coverage), ○ stale/pending (unverified window). Differing confidence is more honest, and more useful, than a uniform claim of correctness.

**2.6 Regime switching for announced-but-pending law.** When a reform was announced with a future effective date (Canada's 2026-11-03 Labour Market Integration factor), we encoded the new tables *before* effectiveness with a date-driven switch, so calculation automatically follows the assessment date across the transition — and, critically, the regression suites for both regimes coexist. After the switch date, the announced tables were verified against the live pages and the pending-change marker was retired. Dual-regime calculation avoids breaking production during legal transitions.

**2.7 One rules base, many delivery layers.** The same YAML rules and pure-function engine serve a CLI, an agent skill, and a browser application (the engine runs unmodified in-browser via Pyodide, so user data never leaves the device). Multi-layer consumption multiplies the value of every maintained rule without any fork of the logic.

## 3. Lessons for the framework

- **Machine-readable publication is the bottleneck, not consumption.** Official pages are frequently JS-rendered (one of our four jurisdictions publishes invitation results only through a JS shell, defeating static diffing); the authoritative scoring tables live in HTML that changes without announcement pages changing. A framework norm of *stable, versioned, machine-readable publication of rules and worked examples by the rule-maker* would remove the largest maintenance cost we bear.
- **Worked examples should be normative.** Our golden tests derive from official examples where jurisdictions publish them, and from hand-derivation where they do not. A norm requiring rule-makers to publish machine-checkable worked examples alongside rules would make community implementations provably correct rather than plausibly correct.
- **Transitions deserve first-class treatment.** Announced-but-pending changes (with effective dates) and mid-cycle corrections both occurred within our first month. A framework should define how implementations encode, verify, and retire pending law.
- **Provenance fields converge.** Independently, we converged on source / effective-date / verified-date / verifier as the minimal provenance set, enforced at build time. We offer this as a candidate minimum for the shared framework.

## 4. Verification status

- 31 golden cases across three pathways, CI-enforced; both CRS regimes (pre/post 2026-11-03) regression-tested.
- Production sentinel: continuous official-page monitoring since 2026-10-30 (24+ runs, zero failures at time of writing), with one genuine mid-cycle policy correction captured.
- Browser engine verified headlessly (Node + Pyodide): identical four-country results to the CLI.
- All policy numbers in the rules base were verified against official pages (canada.ca, Japan ISA, chancenkarte.com) on the dates recorded per file.

## 5. Requests to the framework authors

1. Include build-time provenance enforcement (not just metadata conventions) in the reference framework.
2. Define a norm for official worked-example publication and machine-checkable rule publication.
3. Consider the transition lifecycle (announced-pending → effective → verified) as part of the framework, including how implementations should present regime-dependent results to end users.
4. Recognise community vertical implementations as reference material — we are willing to contribute our schema, test corpus, and sentinel patterns as public goods under CC BY 4.0 / Apache-2.0.

> Disclaimer: this submission describes a technical methodology. It is not immigration advice, and the project's outputs are information products that refer users to licensed professionals.
