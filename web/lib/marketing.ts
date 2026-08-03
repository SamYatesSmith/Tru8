/**
 * Shared marketing constants (C1 entry-point clarity, 2026-07-09).
 */

/**
 * Curated public demo report — the "See a sample record" destination.
 *
 * This is the ONLY way a stranger can evaluate the product without signing up,
 * and it is linked from the homepage hero, the closing CTA and /compare. Treat
 * it as a production surface, not a constant.
 *
 * ⚠️ The previous id (TRU-8723-1E97) had been DEAD for an unknown period —
 * `/api/v1/checks/public/…` 404s for it, and the page answered HTTP 200 carrying
 * "Report Not Found", so nothing flagged it. Verified dead 2026-08-03.
 *
 * Repointed to the 12 June 2026 capture that already backs /compare — chosen
 * because it is live, signed (so /verify works), independently vetted, and shows
 * the thing that actually distinguishes Tru8: of 3 elements, 2 supported and
 * **1 disputed**, over a tier spread of 7 primary / 6 reporting / 4 commentary.
 * A demo where everything comes back green reads as a rubber stamp and undersells
 * the product; a popular belief that turns out contested is the point.
 *
 * Before swapping this id, run `python scripts/check_public_surfaces.py` — it
 * asserts the destination returns a real report, not merely a 200.
 */
export const SAMPLE_REPORT_PATH = '/r/2484b9da-4c94-4042-9fac-61919b93e008';
