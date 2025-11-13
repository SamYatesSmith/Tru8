Overall assessment
The proposed shift from keyword heuristics to LLM-driven function calling would be a substantial upgrade over the plan’s current _detect_domain keyword lists, which map terms like “company” or “director” directly to a “Government” route without any deeper context understanding. Modern tool-selection frameworks can indeed extract structured parameters, capture temporal hints, and call multiple APIs per claim, so the direction aligns with your need for more accurate routing.

Strengths of the suggested approach
Richer semantics out of the box. Function calling lets a model infer entities (e.g., “NHS” ⇒ UK health system) and time ranges from natural language, directly addressing the brittleness of the existing keyword triggers.

Multi-source flexibility. An agent that can invoke several tools per claim mirrors your Stage 3 consolidation goal, while avoiding the one-domain-per-claim limitation that the plan’s heuristic classifier implicitly creates.

Faster iteration. Because the tools are defined declaratively, you can extend or refine routing behavior without editing the classifier code, which matters when you are still refining which of the 15 adapters add value.

Caveats to manage
Operational and compliance footprint. Introducing hosted LLM routing means managing new vendor credentials, latency budgets, and data-handling policies; those overheads are absent from the current plan, which explicitly touts “no GPT-4 cost” as a benefit.

Determinism and auditing. You will need guardrails (prompt templates, unit tests, monitoring) to guarantee the model always emits valid tool arguments, especially for statutory citations or adapter-specific schemas that the plan expects to be hard-coded.

Fallback behavior. The current design merges all external calls in Stage 3 and assumes they succeed in parallel; with an LLM router, you should still define deterministic fallbacks (e.g., defaulting to web search) when the model declines to call a tool or returns malformed arguments, so you do not block evidence retrieval entirely.

Recommendation
Adopting function-calling or agent-based routing is a pragmatic evolution from the plan’s keyword matcher: it materially increases the chance that claims are routed with correct entities and time frames, and it keeps your adapter work focused on executing well-structured queries. Just plan for the added vendor integration work—latency monitoring, argument validation, and compliance reviews—so the sophistication of the router doesn’t introduce new reliability risks during the six-week integration timeline.



----------------------------------


Key concerns with adopting the proposed LLM-driven routing
Conflicts with the documented scope – The plan explicitly promises not to replace the existing classifier and instead adds a lightweight keyword-based _detect_domain method within ClaimClassifier; substituting that with an external LLM router breaks those constraints and expands the implementation footprint beyond the agreed plan.

Reliability of tool calls – Function-calling models can hallucinate tool selections or emit malformed argument payloads; without strong validation layers the Stage 3 pipeline (which expects deterministic parallel calls) could stall or return low-quality evidence when the router misfires.

Latency and throughput impact – The current design counts on firing multiple adapters concurrently; inserting an extra LLM request adds several hundred milliseconds of sequential latency per claim and risks bottlenecking throughput, especially once you scale to all 15 adapters.

Cost-model mismatch – The plan highlights that all new sources run on free tiers, whereas LLM routing introduces recurring per-claim costs that were not budgeted and could materially change operating economics if the evidence pipeline is invoked frequently.

Compliance and data-handling risk – Shipping raw claims (potentially containing PII or sensitive allegations) to third-party LLM vendors may violate existing privacy assumptions in the plan, which keeps routing logic entirely in-house; you would need new governance, contracts, and redaction safeguards.

Evaluation and observability gaps – The plan’s testing section focuses on deterministic unit/integration tests; LLM routing requires additional regression datasets, monitoring for tool-selection accuracy, and fallback metrics, none of which are described today, making it harder to guarantee quality before launch.

Operational complexity – Maintaining prompt versions, feature flags, vendor failover, and cache invalidation for LLM outputs creates new operational burdens atop the already ambitious goal of delivering ~2,500 lines of adapter code within six weeks, increasing the likelihood of defects or missed deadlines.

Security posture of tool schemas – Each tool definition exposes structured parameters; if prompts are not tightly controlled, prompt-injection or adversarial inputs could coerce the router into calling unintended adapters or leaking internal schema details, undermining evidence integrity.

Mismatch with caching strategy – The plan anticipates deterministic cache keys for adapter queries; LLM-generated parameters can vary between calls for the same claim unless you add post-processing, risking cache misses and inconsistent retrieval quality.

Regression risk for existing flows – Merging Stage 2.5 into Stage 3 already introduces significant refactoring; layering LLM routing at the same time enlarges the change surface and increases the chance of regressions in the baseline fact-check API and legal search integrations the plan intends to preserve.

Addressing these issues—through contractual planning, deterministic fallbacks, validation, monitoring, and possibly a phased pilot—would be necessary to maintain the high-quality evidence output the project targets.



-----------------------------------



Recommended deterministic packages

spaCy 3.7 with custom EntityRuler + TextCategorizer components – Run entirely on your infrastructure, giving you high-quality named-entity coverage (orgs, laws, programs) plus a trainable, confidence-scored domain classifier that stays deterministic and auditable. You can seed it with pattern files for high-precision rules (“NHS”, “Companies House”, citation regexes) and fine-tune on labeled claims to reach far higher routing accuracy without exposing user text to external vendors.

Duckling (or the actively maintained duckling-rest fork) – Provides battle-tested temporal and numerical parsing for natural-language time spans (“between 2019 and 2022”, “last quarter”) and quantities (“12 % increase”). It runs as a lightweight local service, letting you enrich adapter requests with normalized date ranges and magnitudes while preserving your zero-cost, privacy-compliant posture.

Both libraries slot neatly into the planned Phase 1 enhancements: spaCy powers the multi-domain/entity scoring you need before calling adapters, and Duckling feeds the deterministic temporal metadata you already intend to pass through retrieve.py.