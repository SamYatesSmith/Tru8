# Structured extraction checkpoint — 8 September 2026

This change addresses **extraction loss before mapping**, finding 4 in the original
hands-on improvement plan. It does not hard-code answers or introduce a new product
direction. Prior checkpoint: evaluation pack `63e89ea`.

## Mechanism and rollout

`services/structured_extraction.py` supplements the existing narrative extractor
with bounded omitted structured content inside HTML main/article regions. Eligible
blocks are small tables, definition lists and compact numeric value/label groups.
It uses generic HTML semantics, not domain names, site classes, rates or dates.
Table captions and headers remain with rows; dedup preserves minus signs and units.
Navigation, headers, footers, controls and explicitly hidden DOM are ineligible.

`ENABLE_STRUCTURED_EXTRACTION=False` remains off by default. Enabled mode uses a
distinct evidence-cache suffix and pipeline fingerprint. No persistent environment
or production setting was changed. Default-off extraction remains unchanged.

Initial research and Compare call the same extraction method; fresh strengthening
sources use the same extraction/capture contract. Recovered text flows into existing
passage receipts and their API/source-detail display. No quotation is manufactured
from an expected test answer. Supplementation adds no publication/effective-date
inference and does not itself change source classifications or relationship weights.

## Measured saved-page results

The audit reads hash-checked saved bytes, not a new live fetch. New and old text is
retained separately at `tmp/structured-extraction-audit-final/`. Reproduce from
`backend` with:

```powershell
python scripts/audit_structured_extraction.py --pack ../tmp/passage-evaluation-2026-09-08-public --output ../tmp/a-new-extraction-audit
```

| Captured source | Legacy characters | Enabled characters | Reviewed change |
|---|---:|---:|---|
| SQLite WAL | 27,246 | 27,246 | None; late BUSY exception already retained |
| SQLite release | 4,268 | 4,268 | None |
| Bank homepage | 668 | 761 | Omitted main-content metric blocks, including rate/decision date |
| Comparison article | 780 | 780 | None; existing header-date contamination remains |
| FDA announcement | 4,761 | 4,800 | Omitted publication block, not an effective-date statement |

Both opposing Bank cases retain the recovered region. The FDA publication addition
does not enter the selected passages for either SELECT case; its recovery must not
be advertised as improved SELECT mapping. All five original narratives are intact.
The inaccessible trial abstract remains unavailable, not scored as a success.

No new unrelated navigation/control blocks were seen among these additions. The
second homepage metric is legitimate page content but not decisive for the Bank
claim; relevance/mapping must still determine its role. Five pages are a targeted
regression sample, not evidence of general extraction accuracy. One-pass extraction
timings are recorded in the report but are not a performance benchmark.

## Bounds and remaining work

- Maximum 12 supplemental blocks / 6,000 characters. Individual blocks over 1,800
  characters (compact metric groups over 600) are skipped whole; large tables are
  not fully addressed. No mid-row truncation.
- Pages lacking main/article regions, JavaScript-only data and CSS-only visibility
  rules can remain unsupported. This does not claim full-document extraction.
- Existing narrative is preserved, including any header date the original
  extractor already admitted. The supplement's exclusions do not clean that old
  text or establish when a fact applies.
- Retained passage windows remain bounded. Source blocks can cross window edges;
  exact citation validation must keep abstaining when an intact basis is absent.
- Default-off full replay establishes compatibility, not enabled model quality.
  Both passage-aware and structured-extraction paths require integrated evaluation
  before activation. Use a 2-by-2 comparison (legacy/structured extraction × legacy/passage-aware mapping) on identical source bytes and frozen shared classifications to separate the two changes. The earlier prepared mapping inputs still contain legacy extraction; use the separately saved enabled texts for the structured arm, never merely flip a flag on pre-extracted inputs. Keep model choice fixed; assess quotation
  entailment, omissions, false directional additions and temporal scope separately.

Validation: **98 backend checks passed** across structure, dates, provenance,
caching/fingerprints, title extraction, distillation, strengthening and real initial
PostgreSQL persistence. The replay result is recorded in the implementation register.
No paid model calls, deployment or runtime-maintained fact values were introduced.
