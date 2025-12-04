# Tru8 LLM Prompt Style Guide

> **Purpose:** Ensure consistency, accuracy, and maintainability across all LLM prompts in the Tru8 fact-checking pipeline.
>
> **Last Updated:** December 2025
>
> **Applies To:** All prompts in `backend/app/pipeline/` and `backend/app/utils/`

---

## Table of Contents

1. [Voice & Persona](#1-voice--persona)
2. [Date & Time Handling](#2-date--time-handling)
3. [Confidence Scales](#3-confidence-scales)
4. [Verdict Vocabulary](#4-verdict-vocabulary)
5. [Error Handling & Uncertainty](#5-error-handling--uncertainty)
6. [Few-Shot Examples](#6-few-shot-examples)
7. [Output Schema Standards](#7-output-schema-standards)
8. [Domain & Freshness Vocabulary](#8-domain--freshness-vocabulary)
9. [Prompt Template](#9-prompt-template)
10. [Anti-Patterns to Avoid](#10-anti-patterns-to-avoid)
11. [Checklist for New Prompts](#11-checklist-for-new-prompts)

---

## 1. Voice & Persona

### Standard Opening

All Tru8 prompts MUST begin with a consistent persona statement:

```
You are a Tru8 fact-checking specialist [role-specific suffix].
```

### Role-Specific Suffixes

| Stage | Suffix |
|-------|--------|
| Extract | "specializing in identifying verifiable claims" |
| Classify | "specializing in content classification" |
| Query Planner | "specializing in evidence retrieval strategy" |
| Judge | "specializing in evidence-based verdict determination" |
| Query Answer | "specializing in answering user questions with evidence" |

### Tone Guidelines

| Do | Don't |
|----|-------|
| Be direct and instructional | Use casual language |
| Use active voice | Be vague or ambiguous |
| Be precise with terminology | Use synonyms interchangeably |
| Acknowledge limitations | Overstate capabilities |

### Example

```
# Good
You are a Tru8 fact-checking specialist specializing in evidence-based verdict determination.

# Avoid
You are an expert fact-checker.
You are a helpful assistant that checks facts.
```

---

## 2. Date & Time Handling

### Mandatory Date Context

**Every prompt that processes temporal content MUST receive the current date.**

Add this block near the top of prompts that handle claims, articles, or evidence:

```
CURRENT DATE CONTEXT:
Today's date is {current_date} (Year: {current_year}).
- Use this date to interpret relative time references ("yesterday", "this week", "recently")
- Use this year ({current_year}) when generating date-specific content
- NEVER hallucinate or guess dates - use only what is provided or explicitly stated
```

### Prompts Requiring Date Context

| Prompt | Requires Date? | Reason |
|--------|---------------|--------|
| Extract | ✅ Yes | Resolve "yesterday", "this week" in claims |
| Classify | ✅ Yes | Determine temporal_context accurately |
| Query Planner | ✅ Yes | Generate correctly-dated search queries |
| Judge | ✅ Yes | Assess evidence recency |
| Query Answer | ⚠️ Optional | Only if answering time-sensitive questions |

### Implementation

In Python, always pass date context:

```python
from datetime import datetime

now = datetime.now()
current_date = now.strftime("%Y-%m-%d")
current_year = now.strftime("%Y")

user_prompt = f"""CURRENT DATE: {current_date} (Year: {current_year})

{rest_of_prompt}
"""
```

### Post-Processing Safeguard

For any prompt that GENERATES text containing dates (e.g., Query Planner), implement deterministic post-processing to catch hallucinated years:

```python
def fix_hallucinated_years(text: str, current_year: int) -> str:
    """Replace recent-but-wrong years with current year."""
    for offset in range(1, 4):  # Check 1-3 years back
        old_year = str(current_year - offset)
        text = re.sub(rf'\b{old_year}\b', str(current_year), text)
    return text
```

---

## 3. Confidence Scales

### Standard Scale: 0-100 Integer

**All prompts MUST use the 0-100 integer scale for confidence.**

| Range | Label | Meaning |
|-------|-------|---------|
| 90-100 | Very High | Near-certain, multiple strong sources agree |
| 75-89 | High | Strong evidence, minor gaps acceptable |
| 50-74 | Moderate | Evidence exists but incomplete or mixed |
| 25-49 | Low | Weak evidence, significant uncertainty |
| 0-24 | Very Low | Insufficient evidence, essentially guessing |

### Prompt Language

```
confidence: Integer from 0-100 indicating certainty level
- 90-100: Very high confidence (strong, corroborating evidence)
- 75-89: High confidence (good evidence, minor gaps)
- 50-74: Moderate confidence (partial evidence)
- 25-49: Low confidence (weak or conflicting evidence)
- 0-24: Very low confidence (insufficient evidence)
```

### Migration Note

Legacy prompts using 0.0-1.0 float scale should be updated:
- `0.95` → `95`
- `0.8-1.0` → `80-100`

---

## 4. Verdict Vocabulary

### Standard Verdicts

Tru8 uses exactly THREE verdict types:

| Verdict | Meaning | When to Use |
|---------|---------|-------------|
| `supported` | Evidence confirms the claim | Strong corroborating evidence from credible sources |
| `contradicted` | Evidence disproves the claim | Direct evidence that the claim is false |
| `uncertain` | Cannot determine | Insufficient, conflicting, or irrelevant evidence |

### Special Cases

| Situation | Verdict | Confidence |
|-----------|---------|------------|
| No evidence found | `insufficient_evidence` | 0 |
| Evidence is off-topic | `uncertain` | Low (25-49) |
| Sources conflict equally | `uncertain` | Moderate (50-60) |
| Claim is technically true but misleading | `supported` with caveats in rationale |

### Verdict MUST NOT

- Invent new verdict types ("partially supported", "likely true")
- Use probability language in verdict field ("probably supported")
- Leave verdict empty or null

---

## 5. Error Handling & Uncertainty

### Every Prompt Must Address Uncertainty

Include a section explaining what to do when the task cannot be completed confidently:

```
WHEN UNCERTAIN:
- Signal low confidence (below 50) rather than guessing
- Explain what information is missing in your rationale
- [Stage-specific fallback behavior]
```

### Stage-Specific Fallback Behaviors

| Stage | When Uncertain | Fallback Behavior |
|-------|---------------|-------------------|
| Extract | Claim is ambiguous | Set confidence low, include in output with caveat |
| Classify | Article spans multiple domains | Use "General", list domains in secondary_domains |
| Query Planner | Claim too vague to query | Generate broader queries, set freshness to "py" |
| Judge | Evidence insufficient | Return `uncertain` verdict, confidence 0-30 |
| Query Answer | Can't answer from evidence | Return low confidence, suggest related claims |

### Example Uncertainty Block

```
HANDLING UNCERTAINTY:
If you cannot confidently complete this task:
1. Do NOT guess or fabricate information
2. Set confidence below 50
3. In your rationale, explain what prevented a confident answer
4. Provide your best attempt with appropriate caveats
```

---

## 6. Few-Shot Examples

### Requirements

Every prompt SHOULD include:

| Example Type | Count | Purpose |
|--------------|-------|---------|
| Typical case | 1-2 | Show expected behavior |
| Edge case | 1 | Show handling of ambiguity |
| Anti-example | 1-2 | Show what NOT to do |

### Format

```
EXAMPLES:

Example 1 - Typical Case:
Input: [example input]
Output: [example output]
Why: [brief explanation]

Example 2 - Edge Case:
Input: [tricky input]
Output: [correct handling]
Why: [explanation of the nuance]

AVOID - Bad Example:
Input: [input]
Wrong output: [incorrect response]
Why this is wrong: [explanation]
Correct output: [what it should be]
```

### Example Quality Criteria

- Examples should be realistic, not contrived
- Use real-world domains (sports, politics, finance)
- Include specific entities, dates, numbers
- Show the complete input→output flow
- Explain the reasoning, not just the answer

---

## 7. Output Schema Standards

### JSON Response Format

All prompts MUST specify exact JSON structure:

```
RESPONSE FORMAT:
Return a valid JSON object with this exact structure:
{
  "field_name": "description and type",
  ...
}

Do not include any text outside the JSON object.
Do not use markdown code blocks.
Return ONLY the JSON.
```

### Standard Fields

These fields should use consistent names across prompts:

| Concept | Standard Field Name | Type |
|---------|-------------------|------|
| Certainty level | `confidence` | Integer 0-100 |
| Explanation | `rationale` | String |
| Final decision | `verdict` | String (supported/contradicted/uncertain) |
| Supporting info | `key_points` or `key_evidence_points` | Array of strings |
| Source references | `sources_used` | Array of integers (indices) |

### Optional Metadata Wrapper

For debugging and traceability, consider wrapping responses:

```json
{
  "_stage": "judge",
  "_timestamp": "2025-12-03T14:30:00Z",
  "result": {
    // Stage-specific content
  }
}
```

---

## 8. Domain & Freshness Vocabulary

### Domain Categories

Use these exact 10 domain names consistently:

| Domain | Scope |
|--------|-------|
| Sports | Athletics, football, basketball, competitive games |
| Politics | Government, elections, policy, legislation |
| Finance | Economics, markets, business, employment |
| Health | Medicine, diseases, healthcare, wellness |
| Science | Research, technology, physics, biology, space |
| Law | Legal cases, court rulings, regulations |
| Climate | Weather, environment, global warming |
| Demographics | Population, census, migration statistics |
| Entertainment | Movies, music, celebrities, arts |
| General | Anything not fitting above categories |

### Freshness Codes

Use these exact codes for evidence recency requirements:

| Code | Meaning | Max Age | Use For |
|------|---------|---------|---------|
| `pd` | Past day | 1 day | Breaking news, live events |
| `pw` | Past week | 7 days | Fast-changing data (standings, polls) |
| `pm` | Past month | 30 days | Periodic updates, recent news |
| `py` | Past year | 365 days | Stable facts, annual data |
| `2y` | Two years | 730 days | Historical, scientific |

### Temporal Relevance (for Judge)

| Value | Meaning |
|-------|---------|
| `current` | Evidence from within required freshness window |
| `recent` | Slightly older but likely still valid |
| `outdated` | Evidence may no longer be accurate |

---

## 9. Prompt Template

Use this template for new prompts or when refactoring existing ones:

```
You are a Tru8 fact-checking specialist specializing in [specific role].

CURRENT DATE CONTEXT:
Today's date is {current_date} (Year: {current_year}).
Use this to interpret relative time references.

TASK:
[Clear, concise description of what the LLM should do]

RULES:
1. [Most important rule]
2. [Second rule]
3. [Continue as needed]

[DOMAIN-SPECIFIC GUIDANCE - if applicable]

HANDLING UNCERTAINTY:
- Signal low confidence (below 50) rather than guessing
- Explain what information is missing
- [Stage-specific fallback]

EXAMPLES:

Example 1 - Typical Case:
Input: [example]
Output: [example]

Example 2 - Edge Case:
Input: [tricky example]
Output: [correct handling]

AVOID:
[Anti-pattern example with explanation]

RESPONSE FORMAT:
Return a valid JSON object:
{
  "field": "type - description",
  "confidence": "Integer 0-100",
  ...
}

Return ONLY valid JSON, no additional text.
```

---

## 10. Anti-Patterns to Avoid

### Prompt Anti-Patterns

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| No persona | Inconsistent behavior | Always start with role statement |
| Vague instructions | Unpredictable output | Be specific and exhaustive |
| No examples | LLM guesses format | Include 2-3 examples |
| No error handling | Fails silently on edge cases | Add uncertainty guidance |
| Hardcoded dates | Becomes stale | Always inject current date |
| Mixed scales | Data inconsistency | Use 0-100 everywhere |

### Output Anti-Patterns

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Markdown in JSON | Parsing failures | Explicitly forbid markdown |
| Inconsistent field names | Code breaks | Use standard field names |
| Missing required fields | Null errors | Specify all required fields |
| Invented verdict types | Logic errors | Enforce exact verdict set |

### Reasoning Anti-Patterns

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Adding qualifiers not in claim | Incorrect verdicts | "Judge ONLY what is explicitly stated" |
| Confusing absence with contradiction | False negatives | "Absence of X ≠ X didn't happen" |
| Pattern matching vs reasoning | Incorrect date math | "Calculate, don't just match" |
| Trusting all sources equally | Unreliable verdicts | Include source credibility assessment |

---

## 11. Checklist for New Prompts

Before deploying a new prompt, verify:

### Structure
- [ ] Starts with standard Tru8 persona
- [ ] Includes current date context (if temporal)
- [ ] Has clear TASK section
- [ ] Has numbered RULES
- [ ] Includes HANDLING UNCERTAINTY section
- [ ] Has 2-3 EXAMPLES (typical + edge case)
- [ ] Shows anti-examples (what NOT to do)
- [ ] Specifies exact JSON RESPONSE FORMAT

### Consistency
- [ ] Uses 0-100 confidence scale
- [ ] Uses standard verdict vocabulary (if applicable)
- [ ] Uses standard domain categories (if applicable)
- [ ] Uses standard freshness codes (if applicable)
- [ ] Field names match other prompts

### Quality
- [ ] Examples are realistic and diverse
- [ ] Edge cases are addressed
- [ ] Uncertainty handling is explicit
- [ ] No hardcoded dates or years
- [ ] Temperature is appropriate (0.1-0.3 for deterministic tasks)

### Testing
- [ ] Tested with typical input
- [ ] Tested with edge case input
- [ ] Tested with adversarial input
- [ ] Output parses as valid JSON
- [ ] Confidence scores are reasonable
- [ ] Reviewed by second person

---

## Appendix A: Current Prompt Inventory

| File | Stage | Prompt Variable | Status |
|------|-------|-----------------|--------|
| `extract.py` | Extract | `self.system_prompt` | ✅ Compliant (persona, date, 0-100, uncertainty, examples) |
| `article_classifier.py` | Classify | `CLASSIFICATION_PROMPT` | ✅ Compliant (persona, date, 0-100, uncertainty, examples) |
| `query_planner.py` | Query Plan | `SYSTEM_PROMPT` | ✅ Compliant (persona, date, uncertainty) |
| `judge.py` | Judge | `self.system_prompt` | ✅ Compliant (persona, 0-100, uncertainty, examples) |
| `query_answer.py` | Answer | `self.system_prompt` | ✅ Compliant (persona, 0-100, uncertainty, examples) |

---

## Appendix B: Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.1 | 2025-12-03 | All prompts aligned to style guide: persona, date context, 0-100 confidence, uncertainty handling |
| 1.0 | 2025-12-03 | Initial guide created from systematic review |

---

## Appendix C: Related Documentation

- `CLAUDE.md` - Project-level AI instructions
- `DESIGN_SYSTEM.md` - Frontend design standards
- `backend/app/core/config.py` - Model configuration settings

---

*This guide should be updated whenever prompt patterns evolve or new best practices emerge.*
