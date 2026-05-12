import Image from 'next/image';

/**
 * Stitch W-01 Product Preview
 *
 * Replaces the previous placeholder video. Split layout:
 *  - LEFT: product screenshot (Librarian view by default) inside a 1px
 *    zinc-bordered frame with a mono micro-label.
 *  - RIGHT: a faithful /agent/quick response snippet (real shape from
 *    response_builder._compute_landscape + _meta block).
 *
 * Stitch theme: white surfaces, 1px zinc borders, mono micro-labels,
 * no shadows on the content frames. The JSON block uses a dark zinc-950
 * surface — the only dark element, mirroring the developer page.
 *
 * NOTE: the screenshot file at /imagery/screenshots/librarian-landscape.png
 * is a placeholder until real captures land. See
 * audit/2026-05-12_homepage_screenshots.md for the capture spec.
 */
export function StitchProductPreview() {
  return (
    <section id="preview" className="py-24 md:py-32 bg-white">
      <div className="max-w-7xl mx-auto px-6">
        {/* Header */}
        <div className="mb-12 md:mb-16 max-w-2xl">
          <span className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400 mb-4 block">
            Module — See It Work
          </span>
          <h2 className="text-3xl md:text-4xl font-light tracking-tight text-zinc-900">
            One submission. <span className="font-bold">Two surfaces.</span>
          </h2>
          <p className="text-sm md:text-base text-zinc-500 leading-relaxed mt-4">
            The same evidence research powers the browser dashboard and the agent API. Read it in the
            Librarian on the left, or consume it as structured JSON on the right.
          </p>
        </div>

        {/* Split panels */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 lg:gap-8">
          {/* LEFT — product screenshot */}
          <div className="border border-zinc-200 bg-white overflow-hidden flex flex-col">
            <div className="flex items-center justify-between px-5 py-3 border-b border-zinc-100">
              <span className="font-mono text-[10px] tracking-[0.3em] uppercase text-zinc-400">
                Librarian view — Dashboard
              </span>
              <span className="font-mono text-[10px] text-zinc-300">/dashboard/check/[id]</span>
            </div>
            <div className="relative aspect-[4/3] bg-zinc-50">
              <Image
                src="/imagery/screenshots/librarian-landscape.png"
                alt="Tru8 Librarian view — evidence classified by tier (primary, reporting, commentary) and type (data, official, news, analysis, opinion, academic)"
                fill
                sizes="(min-width: 1024px) 50vw, 100vw"
                className="object-cover object-top"
                priority={false}
              />
            </div>
          </div>

          {/* RIGHT — JSON snippet */}
          <div className="border border-zinc-200 bg-white overflow-hidden flex flex-col">
            <div className="flex items-center justify-between px-5 py-3 border-b border-zinc-100">
              <span className="font-mono text-[10px] tracking-[0.3em] uppercase text-accent">
                POST /agent/quick — Response
              </span>
              <span className="font-mono text-[10px] text-zinc-300">200 OK</span>
            </div>
            <pre className="bg-zinc-950 text-zinc-300 px-5 py-5 overflow-x-auto text-[11px] md:text-xs font-mono leading-relaxed flex-1">
{`{
  "id": "chk_8f3a...",
  "status": "complete",
  "claims": [
    {
      "id": "clm_01",
      "text": "Global average temperature rose 1.1°C since pre-industrial times",
      "claimMap": {
        "normalisedClaim": "...",
        "claimType": "scientific",
        "elements": [
          {
            "elementId": "el_01",
            "description": "1.1°C rise figure",
            "state": "supported",
            "evidenceRefs": [
              { "evidenceId": "ev_a1", "relationship": "supports" },
              { "evidenceId": "ev_b2", "relationship": "supports" }
            ]
          }
        ],
        "orientation": "Evidence converges on the 1.1°C figure across primary and academic sources."
      }
    }
  ],
  "_meta": {
    "executedTier": "quick",
    "chargedPence": 7,
    "landscape": {
      "elementCount": 4,
      "elementStates": { "supported": 3, "unresolved": 1 },
      "evidenceDensity": 24,
      "sourcesConsidered": 24,
      "sourceDiversity": {
        "tierSpread": { "primary": 6, "reporting": 12, "commentary": 6 },
        "uniqueDomains": 18,
        "typeCoverage": 5
      },
      "freshness": { "freshestDaysAgo": 3, "dateSpanDays": 412 },
      "gaps": [{ "reason": "no_academic_sources" }]
    },
    "limitations": ["heuristic_classification", "single_query_per_element"]
  },
  "_manifest": {
    "checkId": "chk_8f3a...",
    "landscapeHash": "9c14...",
    "signature": "hmac-sha256:...",
    "verifyUrl": "/verify/chk_8f3a..."
  }
}`}
            </pre>
          </div>
        </div>

        {/* Footnote */}
        <p className="text-xs text-zinc-400 mt-6 font-mono">
          Response shape is the live /agent/quick contract. Field values are illustrative.
        </p>
      </div>
    </section>
  );
}
