"""P2 diagnostic probe (NOT product code; uncommitted).

Captures the REAL wired path for the UK-gov adapter cluster on the reference
claims that 0-yielded in prod, to separate three candidate root causes:
  (I)   domain routing   -> is_relevant_for_domain(classified_domain)
  (II)  query shape      -> prepare_query output (sentence fallback?)
  (III) response handling-> live yield at classified domain vs a permissive domain

Runs the actual extract LLM -> typed entities -> {type->label} boundary remap ->
each adapter's prepare_query -> live search (keyless adapters only).

Run from backend/:  python -m scripts.probe_prepare_query
"""

import asyncio

from app.pipeline.extract import ClaimExtractor
from app.services.api_adapters.legal import GovUKAdapter, HansardAdapter
from app.services.api_adapters.economic import ONSAdapter
from app.services.api_adapters.business import CompaniesHouseAdapter

# (label, claim_text, classified_domain, jurisdiction) — shapes from the audit doc.
REFERENCE_CLAIMS = [
    (
        "BoE rate cut — bare sentence (focused)",
        "The Bank of England cut interest rates to 0.25% in August 2016.",
        "Finance",
        "UK",
    ),
    (
        "BoE rate cut — paragraph (article)",
        "In August 2016, the Bank of England's Monetary Policy Committee voted to cut "
        "the base interest rate to 0.25%, the first reduction since 2009, in response "
        "to the Brexit referendum. Governor Mark Carney also announced additional "
        "quantitative easing measures.",
        "Finance",
        "UK",
    ),
    (
        "Autumn Statement — bare sentence (focused)",
        "The Chancellor delivered the Autumn Statement in November 2023.",
        "Finance",
        "UK",
    ),
    (
        "Autumn Statement — paragraph (article)",
        "The Chancellor of the Exchequer delivered the Autumn Statement to Parliament "
        "in November 2023, setting out the government's tax and spending plans. The "
        "statement included cuts to National Insurance and changes to business taxation.",
        "Finance",
        "UK",
    ),
]


def to_label(entities):
    # NF-15 boundary: extract emits {text,type}; adapters read {text,label}. Straight rename.
    return [
        {"text": e.get("text", ""), "label": e.get("type", "")}
        for e in (entities or [])
    ]


async def main():
    extractor = ClaimExtractor()
    print("GOOGLE_AI key present:", bool(extractor.google_ai_api_key))
    govuk, hansard, ons, ch = (
        GovUKAdapter(),
        HansardAdapter(),
        ONSAdapter(),
        CompaniesHouseAdapter(),
    )
    adapters = [govuk, hansard, ons, ch]

    for name, claim_text, domain, juris in REFERENCE_CLAIMS:
        print("\n" + "=" * 84)
        print(f"CLAIM: {name}\n  input: {claim_text}\n  classified: {domain}/{juris}")
        res = await extractor.extract_claims(claim_text, {})
        if not res.get("success"):
            print("  EXTRACT FAILED:", res.get("error"))
            continue
        for claim in res.get("claims", []):
            ct = claim.get("claim_text") or claim.get("text") or claim_text
            ents = claim.get("key_entities") or []
            lab = to_label(ents)
            print(f"\n  extracted claim_text: {ct}")
            print(f"  key_entities: {[(e.get('text'), e.get('type')) for e in ents]}")

            print("  --- per adapter: (I) routing | (II) query | (III) live yield ---")
            for adp in adapters:
                try:
                    q = adp.prepare_query(ct, lab)
                except Exception as e:
                    q = f"<ERR {e}>"
                relevant = adp.is_relevant_for_domain(domain, juris)
                print(
                    f"    {adp.api_name:26s} relevant({domain})={relevant!s:5s} q={q!r}"
                )

            # (III) live yield for keyless topic-keyword adapters, at classified domain
            #       AND at a permissive domain to isolate routing from query.
            for adp in (govuk, hansard):
                permissive = "Politics"
                try:
                    q = adp.prepare_query(ct, lab)
                    n_classified = len(adp.search(q, domain, juris, lab))
                    n_permissive = len(adp.search(q, permissive, juris, lab))
                    print(
                        f"    LIVE {adp.api_name:21s} q={q!r} "
                        f"-> {domain}:{n_classified}  {permissive}:{n_permissive}"
                    )
                except Exception as e:
                    print(f"    LIVE {adp.api_name} ERROR {e}")


if __name__ == "__main__":
    asyncio.run(main())
