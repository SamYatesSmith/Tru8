🧭 Tru8 Credibility Integration Guide – v2
Consultant Instruction Document for Claude Code

Objective:
Integrate a comprehensive, credibility-aware framework into Tru8’s existing 5-stage pipeline while maintaining modular design, safety, transparency, and long-term trustworthiness.

Core Principles:

Learn before coding — study first, modify second.

No duplication — respect DRY principles throughout.

Accuracy is valued above speed.

When uncertain, abstain.

Preserve clarity, citations, and composure under all failure states.

🔐 01 — Conduct & Coding Standards

Research First: Read all relevant pipeline, service, and model files before making any changes.

Integrate Cleanly: All new logic should live inside isolated services or helpers; never inline large code blocks.

Reuse Existing Systems: Use existing cache, telemetry, and logging infrastructure.

Fail Safely: On partial data, degrade gracefully — return “uncertain” rather than error or silence.

Respect Data Flow: Preserve each stage boundary (Ingest → Extract → Retrieve → Verify → Judge → Save).

⚙️ 02 — Architectural Overview

Integrations attach to the pipeline as extensions, not replacements:

Stage	New Integration
Retrieve	Fact-check pre-search, domain credibility scoring, red-flag filtering, temporal awareness
Verify	Credibility-weighted NLI scoring
Judge	Consensus + abstention logic, nuanced verdict labels
Finalize/Save	Metadata enrichment for credibility context
UI Layer	Expanded citations + Source Leaderboard view
🧠 03 — Fact-Check Layer

Goal: prevent re-validating known misinformation.

Add service FactCheckService to query ClaimReview data and APIs (Snopes, Full Fact, PolitiFact, etc.).

Only store verdict summaries + URLs — never article text.

Cite sources properly:

“According to Snopes (2024-09-12): rated False.”

Run before Brave Search; if found, skip retrieval and use verdict directly.

Cache results to avoid API overuse.

Mark all fact-check evidence clearly as source_type="factcheck".

Legal review required prior to public use.

🧰 04 — Domain Credibility Framework

Goal: assign objective reputation tiers to domains.

Maintain single config file source_credibility.json containing:

Tiered allowlists (academic, gov, tier1_news, etc.)

Blacklist (known misinformation domains)

Red-flag keywords (manipulative phrasing)

Add service SourceCredibilityService to return base credibility + reason.

Apply results post-retrieval, pre-verification.

No hardcoded domains anywhere else — this JSON is the global source of truth.

⚖️ 05 — Consensus & Abstention Logic

Goal: make verdicts defensible, not fast.

Require ≥3 independent sources with credibility ≥0.8 before Supported or Contradicted verdicts.

Otherwise → Uncertain or Needs Primary Source.

Outputs must include: verdict, confidence, rationale, consensus_count, independent_sources.

Judge LLM explains why a verdict was cautious or conclusive.

If evidence insufficient → abstain automatically.

🧱 06 — Database Enrichment Schema

Goal: store credibility metadata cleanly.

Add nullable columns to Evidence:

source_tier: str

verification_status: str

fact_check_result: JSON

red_flags: JSON
Populate automatically via enrichment helper during Retrieve/Verify.
Default None values must not break queries or serialization.

🔍 07 — Red-Flag Classifier

Goal: detect manipulative or low-integrity writing.

Create RedFlagDetector under services/content_filter.py.

Rule-based first: tone, missing authors, all-caps, hyperbole.

Future: train lightweight classifier using labelled examples.

Adjust credibility_score downward if triggered.

Store both flags and rationales (red_flags list) for user transparency.

🧮 08 — Source Reliability Tracking + Leaderboard

Goal: build a transparent trust index.

Backend Logic

Table: SourceStats(domain, total_claims, accurate_claims, disputed_claims, score).

Update automatically when a claim is finalised.

Use Wilson score interval or Bayesian averaging for fair weighting — avoids distortion from small datasets.

Example:

score = (accurate_claims + 1.9208) / (total_claims + 3.8416)

UI Implementation

New page: “Source Leaderboard” (Professional tier only).

Columns: Rank | Source | Reliability % | Verified Claims | Contradicted Claims | Trend | Last Updated.

Optional charts using Chart.js or Recharts.

Sort and filter options (region, media type, topic).

Refresh asynchronously every 10–15 minutes or upon new data.

Disclaimer:

“Scores reflect automated statistical analysis of Tru8 fact-check outcomes and do not represent editorial judgment.”

🧭 09 — Temporal Context Awareness

Goal: prevent outdated context errors.

Detect temporal references in claims (“in 2021”, “said”, “announced”).

Restrict search range accordingly.

Flag articles >18 months outside reference period as temporal_mismatch.

Down-weight or exclude such evidence in final verdict logic.

🧾 10 — Citations & Proof Presentation

Goal: strengthen transparency and academic credibility.

Each displayed evidence card must include:

Full citation (source, title, author if available, publication date, URL).

Citation format similar to UK academic standards.

Graceful failure: if citation fields missing, display partial data with a fallback notice (“citation data incomplete”).

Citation retrieval failures must never interrupt pipeline flow.

Encourage consistent style across all UI elements.

🧪 11 — Testing & Accuracy Standards

Testing priorities:

Known false claim → Contradicted

Weak or mixed claim → Uncertain

Consensus check → must need ≥3 credible sources

Fact-check hit → must override normal retrieval

Performance expectation:

Focus on correctness over speed.

If a complete check takes 20–30 seconds but is accurate, that is acceptable.

Cache and concurrency may still reduce average latency naturally.

Explainability:
Every verdict must output a clear reasoning trail showing how and why the conclusion was reached.

🧱 12 — Safety, Fairness & Maintenance

Legal: all fact-check integrations must comply with fair-use and citation law.

Bias mitigation: maintain ideological and geographic diversity in source tiers.

Data updates: refresh source_credibility.json monthly (manual script or scheduled task).

Feature toggles: wrap each new component in env flags (ENABLE_FACTCHECK, ENABLE_LEADERBOARD, etc.).

No deployment instructions included — assume staging and testing environments already exist.

✅ Final Instructions for Claude Code

Analyse the current codebase before any modifications.

Integrate features as modular services, not inline edits.

Uphold DRY, SOLID, and defensive programming standards.

Handle missing data gracefully; never crash on nulls.

Maintain explainability across all outputs.

Document all new functions, models, and config structures clearly.

Optimise only after correctness is proven.

End of Document
Prepared by: Strategic Integration Consultant for Tru8
Purpose: To guide Claude Code in safely upgrading Tru8’s credibility engine into a transparent, auditable truth-verification system.