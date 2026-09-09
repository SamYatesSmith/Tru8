# Human review of directional relationships — 2026-09-09 regrade records

Astra's 8/10 gate (`tmp/tru8-hands-on/tru8-route-to-eight.md`, Evidence fidelity): a knowledgeable human reviews at least 200 directional relationships; target at least 95% justified support/challenge labels, misses reported by kind, a second reviewer on ambiguous cases.

These sheets carry **137 directional labels** across 14 records from the final default-configuration regrade of Astra's 14 inputs (`tmp/astra-regrade-final/`, branch `codex/evidence-quality`).

## Protocol

1. Open a sheet. For each label, read the element, the system's reasoning and the passage the mapper was given. Decide **Justified? Y / N / Unsure** — is the label warranted by what the source says about *that* element?
2. If N: name the kind — `direction`, `absent`, `scope`, `recital`, `other` — and write one line.
3. Record answers in `labels.csv` (columns `justified`, `kind`, `note`), one row per label; `label_id` matches the heading in the sheet.
4. Do not look up the source live unless the passage is insufficient to decide; if you do, say so in the note. The question is whether the label is justified by what the system read.
5. Context-only and set-aside lists are not graded; flag one only if you think it should have been directional or a rule fired wrongly.

## Tally

`justified rate = Y / (Y + N)`; report Unsure separately; report kinds of N. Anything under 95% names the next build.

| Record | Directional labels |
|---|---:|
| t01_brexit | 14 |
| t02_select | 12 |
| t03_creatine | 7 |
| t04_jwst | 16 |
| t05_bankrate_425 | 3 |
| t06_sweden_focus | 12 |
| t07_sqlite_busy | 11 |
| t08_ev | 17 |
| t09_sqlite_url | 17 |
| t10_lantern | 0 |
| t11_inflation | 4 |
| t12_venus_image | 10 |
| t13_sweden | 8 |
| t14_bankrate_375 | 6 |

| **Total** | **137** |