# Claim Map Contract — v1

**Date:** 2026-02-12
**Status:** Canonical. All API responses, DB storage, harness comparison, and frontend rendering derive from this contract.
**Depends on:** `2026-02-12_track-b-deep-dive.md` (codebase impact analysis)

---

## 1. ClaimMap Object

One ClaimMap per claim within a check. This is the sole first-class analysis output.

```jsonc
{
  "claim_id": "<string>",             // Existing claim identifier from Check/Claim model
  "normalised_claim": "<string>",     // Normalised claim text (from decomposition stage)
  "claim_type": "<ClaimType>",        // Classified at decomposition (authority), not extraction
  "elements": [                       // 1–5 elements (hard cap 5). Order = decomposition order.
    {
      "element_id": "e1",             // Sequential: "e1".."e5". Assigned by decomposition order.
      "description": "<string>",      // What must hold for the claim to stand
      "evidence_refs": [              // Evidence mapped to this element (from mapping stage)
        {
          "evidence_id": "<string>",  // Stable ID referencing an item in the flat evidence list
          "relationship": "<EvidenceRelationship>"  // How this evidence relates to this element
        }
      ],
      "state": "<ElementState>",      // Assigned by mapping stage
      "uncertainty": "<string|null>"  // Optional. One sentence max. Element-scoped.
    }
  ],
  "orientation": "<string>",          // Mechanically derived from element states. Not LLM-generated.
  "metadata": {
    "decomposition_model": "<string>",  // Model used for decomposition
    "mapping_model": "<string>",        // Model used for evidence mapping
    "element_count": "<int>",           // Convenience: len(elements)
    "completed_at": "<iso8601>"         // Timestamp of Claim Map completion
  }
}
```

---

## 2. Enums

### ClaimType
| Value | Meaning |
|-------|---------|
| `empirical` | Verifiable factual assertion |
| `definitional` | Defines or categorises a concept |
| `causal_interpretive` | Asserts causal relationship or interprets mechanism |
| `predictive` | Makes forward-looking assertion |
| `normative_flagged` | Contains value judgment. System labels only — does not adjudicate. May decompose into empirical sub-elements. |

### ElementState
| Value | Meaning |
|-------|---------|
| `supported` | Mapped evidence is predominantly supportive, with no significant challenging evidence |
| `disputed` | Both supporting and challenging evidence are mapped to the element |
| `unresolved` | No meaningful supporting or challenging evidence is mapped |

Note: No numeric thresholds are implied. Element state is a qualitative assessment made by the mapping LLM during Phase 2. The mapping prompt assigns states based on the distribution of `supports`/`challenges` relationships, not counts or ratios.

### EvidenceRelationship
| Value | Meaning |
|-------|---------|
| `supports` | Evidence corroborates or confirms this element |
| `challenges` | Evidence contradicts or undermines this element |
| `context` | Evidence is relevant background or scope-setting but does not clearly support or challenge |

Note: Some retrieved evidence provides context (definitions, timelines, scope) without taking a directional stance. Forcing binary classification would mislabel or discard useful evidence. Element state derivation remains based on the presence/absence of `supports` and `challenges` relationships; `context` evidence does not influence element state.

---

## 3. Evidence Item (flat list, per-claim)

Existing evidence dict with two new fields. All current fields preserved.

```jsonc
{
  // --- NEW FIELDS ---
  "evidence_id": "<string>",           // Stable. Assigned at retrieval. Persists through pipeline.
  "element_ids": ["e1", "e3"],         // Derived convenience field (see Section 3.1)

  // --- EXISTING FIELDS (preserved) ---
  "url": "<string>",
  "title": "<string>",
  "snippet": "<string>",
  "domain": "<string>",
  "source_type": "<string>",
  "credibility_score": "<float>",
  "final_score": "<float>",
  "llm_relevance_score": "<float|null>",
  "content_hash": "<string|null>"
  // ... other existing fields unchanged
}
```

### 3.1 Source of Truth for Evidence–Element Association

- `elements[].evidence_refs` in the Claim Map is the **source of truth** for:
  - which evidence items are associated with an element
  - how each evidence item relates to that element (relationship)
- `element_ids` on the evidence item is a **derived convenience field**:
  - populated to support internal filtering, replay, and debugging
  - must be consistent with the associations present in `elements[].evidence_refs`
  - does not carry relationship semantics (no `supports`/`challenges`/`context` information)

Relationship semantics live only in the Claim Map, not on the evidence item.

### Evidence ID Rules

- **Assigned at:** Retrieval time (earliest pipeline stage for this evidence item)
- **Persists through:** Dedup, scoring, capping, mapping — never reassigned
- **Included in:** Freeze data (for replay determinism)
- **Uniqueness:** Unique within a check
- **Generation scheme:** Implementation detail (content-hash or UUID both acceptable so long as the above properties hold). Frozen replay injects evidence with IDs already set from baseline.

---

## 4. Build Phases (Incremental Construction)

The Claim Map is built in two stages. The DB stores the completed object.

### Phase 1 — Decomposition Stage (new Stage 4)

**Input:** Raw claim text (from extraction)
**Output:** Partial Claim Map scaffold

Fields written:
- `normalised_claim`
- `claim_type`
- `elements[]` with `element_id` + `description`
- `metadata.decomposition_model`

Fields NOT yet populated:
- `elements[].evidence_refs` → empty
- `elements[].state` → null
- `elements[].uncertainty` → null
- `orientation` → null

### Phase 2 — Evidence Mapping Stage (replaces Stage 5 Judge)

**Input:** Partial Claim Map + flat evidence list (post-retrieval, post-filtering, with `element_ids` tagged)
**Output:** Completed Claim Map

Fields completed:
- `elements[].evidence_refs` → populated from tagged evidence
- `elements[].state` → assigned by mapping LLM
- `elements[].uncertainty` → optional, assigned by mapping LLM
- `orientation` → mechanically derived (see Section 6)
- `metadata.mapping_model`
- `metadata.element_count`
- `metadata.completed_at`

---

## 5. Orientation Line — Derivation Rule (v1)

Mechanical. No LLM. Deterministic given element states.

**Tone constraint:** Orientation lines describe the distribution of element states. They must not assert truth, correctness, or falsity of the claim. They must be fully derivable from element states alone. The orientation line is a derived descriptor, not an interpretive layer.

### Rule

1. Count elements by state
2. Apply template based on distribution

### Templates

**Unanimous state:**
```
All {N} required elements are evidentially {state}.
```

**Mixed states (majority exists):**
```
{majority_count} of {total} required elements are evidentially {majority_state}; {remainder_description}.
```

**No majority (all different or tied):**
```
Evidence is mixed across {total} required elements: {count} {state}, {count} {state}, {count} {state}.
```

### Examples

| Element States | Orientation Line |
|---|---|
| [supported] | "The single required element is evidentially supported." |
| [supported, supported, supported] | "All 3 required elements are evidentially supported." |
| [supported, supported, disputed] | "2 of 3 required elements are evidentially supported; 1 is disputed." |
| [supported, disputed, unresolved, unresolved] | "2 of 4 required elements are unresolved; 1 is supported and 1 is disputed." |
| [supported, disputed, unresolved] | "Evidence is mixed across 3 required elements: 1 supported, 1 disputed, 1 unresolved." |

### Special case: single element
```
The single required element is evidentially {state}.
```

---

## 6. Bounds

| Dimension | Min | Max | Configurable v1? |
|-----------|-----|-----|-------------------|
| Elements per claim | 1 | 5 (hard cap) | No |
| Claims per check (article mode) | 1 | 5 (hard cap) | No |
| Claims per check (focused mode) | 1 | 1 | No |
| Evidence per element | 0 | Unbounded (controlled by retrieval caps + domain capping) | Indirectly (via existing caps) |
| Uncertainty note length | 0 | 1 sentence | No |
| Orientation line | 1 sentence | 1 sentence | No |

---

## 7. Determinism Properties

| Property | Deterministic? | Notes |
|----------|---------------|-------|
| Element IDs | Yes | Sequential by decomposition order |
| Evidence IDs | Yes | Assigned at retrieval, persists through pipeline |
| Element descriptions | No (LLM) | May vary across runs (decomposition LLM noise) |
| Element states | No (LLM) | May vary across runs (mapping LLM noise) — analogue of verdict noise |
| Evidence mapping | No (LLM) | Which evidence maps to which element may vary |
| Orientation line | Yes (given states) | Mechanical derivation from element states |
| Claim type | No (LLM) | Classified at decomposition — may vary |

**Harness implication:** Element state changes across runs are the analogue of verdict flips. The harness Gate 2 replacement should classify element-state flips the same way it currently classifies verdict flips (hard_fail vs llm_noise).

---

## 8. What This Contract Does NOT Specify

These are implementation details resolved during PR development:

- Evidence ID generation scheme (hash vs UUID)
- Decomposition prompt text
- Mapping prompt text
- Seed retrieve trigger conditions (deferred; v1 has no seed retrieve)
- DB column layout (single `claim_map` JSONB vs normalised tables)
- API response envelope shape (pagination, error format)
- Frontend rendering
- Extraction-time claim type hint (optional, non-binding, not required for v1)

---

## 9. Relationship to Other Contracts

| Document | Relationship |
|----------|-------------|
| `2026-02-12_track-b-deep-dive.md` | Codebase impact analysis — identifies what changes per file |
| Track B PR specs (to be written) | Derive scope and sequencing from this contract |
| Harness Gate 2 replacement | Derives comparison logic from ClaimMap shape + determinism properties |
| API contract (to be written) | Response shape wraps this ClaimMap object |
| Frontend types (to be written) | TypeScript types mirror this contract |
