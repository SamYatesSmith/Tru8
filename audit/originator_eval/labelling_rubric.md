# Labelling rubric: did this page's publisher produce the information?

Written 2026-09-30, separately from the originator-review prompt. **Version 2** (same day): one rule corrected after the founder's audit of 30 v1 labels: who is speaking decides forum, issue and mailing-list content, not the format. No worked example here comes from any item you will label.

## The one question
For each page: **did the organisation that publishes this page produce the information the page presents?**
Judge the page as a whole, from its URL, host, title and text. Ignore how trustworthy or well known the publisher is. A small blog that publishes its own measurements produced them; a famous institution's explainer of someone else's figures did not.

## Labels
- **originator**: the publisher produced the information itself. This includes:
  - its own data, measurements, survey, study, trial or model output;
  - its own official record, decision, ruling, filing or statement about itself;
  - its own documentation of its own product, software, service or mission;
  - a new dataset or estimate it built by compiling or modelling other bodies' raw data (the new series is its own);
  - a complete, unaltered copy of an original document hosted elsewhere (e.g. a government report's PDF on a university server). Label the document, not the host;
  - a project's own maintainers or contributors describing their own code, behaviour, bug, decision or proposed change, in whatever format (issue, forum post, mailing-list message, README).
- **not_originator**: the page passes on information produced by someone else. This includes:
  - explainers, guides, glossaries, encyclopaedia entries, textbook and course pages, FAQs;
  - summaries or write-ups of another body's study, data, trial or decision;
  - calculators, comparison or price sites, dashboards and profiles that re-display another body's figures;
  - mirrors, packaging or third-party copies of documentation for a product the publisher does not make;
  - forum posts, issue threads, mailing-list messages, Q&A and comments by people who are NOT the project's own maintainers or the publisher, even on the product owner's own site. The format alone never decides it; who is speaking does.
- **unclear**: the text you have does not let you tell (e.g. mostly navigation, cookie or login text, or too short).

## Rules
- Use only what is in front of you. Do not browse. You may use general knowledge of who an organisation is (e.g. that a given agency runs a given survey).
- When a page mixes both (an organisation's own figures plus an explainer), label by what the page is mainly presenting.
- A news or trade outlet reporting someone else's findings is **not_originator**; its own investigation or survey is **originator**.
- Do not guess to avoid `unclear`. `unclear` is a valid, useful answer.

## Output per item
`{"id": "...", "label": "originator | not_originator | unclear", "why": "<one short sentence>"}`
