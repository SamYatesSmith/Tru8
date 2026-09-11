# Mass-contact methodology — collect everyone first, then contact by segment and route

**Status:** DRAFT 2026-09-10, written the hour the founder said *"Everybody and anybody whom may show an interest in the product. Any way to contact them, is welcome. Collect all recipient information and then arrange a mass contact styled methodology."*
**Companion:** `audit/2026-09-10_outreach_volume_plan.md` (segments, infrastructure, kit).
**⚠️ 2026-09-11: the operating procedure is now `audit/2026-09-11_outreach_operating_procedure.md`.** Phases 1–2 below (collect, consolidate) are done and still describe the list. Phases 3–5 (subdomain warm-up, sequencer waves of 100–300, 3 %/2 % thresholds) are DEFERRED until the wave-1 verdict; sends now go by hand, ≤25/day, every record read, from the queue file `audit/recipients/queue.csv`.
**Data lives in** `audit/recipients/` — gitignored; never committed; the master is `master.csv`, rejections `master.rejected.csv`.

---

## Phase 1 — COLLECT (running now)

**Method.** Six parallel collectors, one per segment family, each searching public sources and fetching the page where a contact route appears. Segments in the first sweep: UK legal · UK journalists and desks · independent newsletters and podcasts · think-tanks, comms, research integrity, OSINT · developer directories, newsletters and press · journalism schools, libraries, media literacy, civic and community news. Second sweep candidates (▶ founder): US/EU journalists, corporate research/insight teams, insurers and due-diligence firms, MPs' researchers, NHS communications, trade bodies, investor-relations, academic societies.

**Row schema** (`audit/recipients/README_schema.csv`):
`segment, name, role, organisation, country, route_type, route, route_seen_at_url, current_topic, notes, collected_on`
`route_type ∈ email · contact_form · linkedin · x · bluesky · substack · org_inbox · press_office · submission_form · github`

**Rules, enforced by `backend/scripts/merge_recipients.py`, not by convention:**
1. **No route without the page it was seen on.** A row without an `http(s)` `route_seen_at_url` is rejected.
2. **No guessed addresses.** An email is recorded only when the collector saw it on a fetched page. Domain-mismatch between the address and the page it was seen on is flagged for review.
3. **No personal mailboxes** (gmail, hotmail, outlook, yahoo, icloud, proton) even when published — those people are reached by Substack, LinkedIn, X/Bluesky or a form instead. UK PECR treats individual subscribers differently from corporate ones; we stay on the corporate side of the line.
4. **Dedup** by route, and by (name, organisation); the row with the richer `current_topic` wins.
5. **Every rejection is written out with a reason**, so the collector fixes the source, not the symptom.

**What "everybody and anybody" means in practice:** a row is welcome from any segment, but every row still needs a route we may lawfully use and a page that proves it. Breadth comes from more segments and more sources, never from looser rules.

## Phase 2 — CONSOLIDATE AND ENRICH (after the sweep)

1. Merge: `python backend/scripts/merge_recipients.py audit/recipients/*.csv --out audit/recipients/master.csv`.
2. Founder skims `master.rejected.csv` (should be short) and the `review_flags` column.
3. **Route priority per row** — the mass motion uses the best route we hold: `email` > `org_inbox`/`press_office` > `contact_form` > `linkedin` > `substack` > `x`/`bluesky`. Rows with only a social route go to the social batch (Phase 4), not the email batch.
4. **Topic tagging:** every row gets one `topic_key` from the segment's live topic list (the 12 topic records in the volume plan). Rows with no live topic get the segment's default record.
5. **Suppression sheet** created (`audit/recipients/suppression.csv`): anyone who opts out, bounces hard, or asks not to be contacted, plus the five bespoke targets (they get the bespoke note, never the mass one) and anyone the founder knows personally.

## Phase 3 — INFRASTRUCTURE (parallel, ▶ founder)

- **Sending subdomain** (e.g. `hello@mail.trueight.com`) with its own SPF/DKIM/DMARC; warm-up 2–3 weeks. The root `sam@trueight.com` stays for bespoke sends and replies.
- **Sequencer** (recommendation: Apollo — list enrichment + sequencer in one; alternatives Instantly / Lemlist / Smartlead). Requirements: CSV import with custom fields, per-row link with `?src=<segment>-<topic>`, automatic opt-out footer, bounce and reply detection, throttle ≤ 50/day/mailbox to start, suppression-list import.
- **Tracking:** `?src=` → `User.signup_source` (live); PostHog `/r/` opens (consented only); replies to the founder's inbox.

## Phase 4 — CONTACT, in waves

| wave | who | route | volume | message |
|---|---|---|---|---|
| 0 | the five bespoke targets | as per the send sheet | 5 | bespoke notes (already drafted) |
| 1 | email + org_inbox rows, segments 1–2 | sequencer, warmed subdomain | first 100, then to 300 | K3 3-touch sequence: day 0 record · day 4 nudge · day 10 second record |
| 2 | email rows, remaining segments | same | +300 | same shape, segment copy |
| 3 | submission_form / github rows (developer directories) | by hand or PR | ~30 | listing submissions + the K7 launch post |
| 4 | linkedin / substack / x / bluesky rows | by hand from the founder's accounts, ≤ 20/day | ongoing | one-line note + record link; DM copy from K3 cut to 40 words |
| 5 | contact_form rows | by hand, ≤ 15/day | ongoing | K3 day-0 copy pasted |

**Every message:** real sender name, what Tru8 is in one clause, the record link for THEIR topic, one question, opt-out line (email) or nothing to unsubscribe from (DMs). No attachments in wave 1 (deliverability); the one-pager is a link.

## Phase 5 — MEASURE AND ADJUST

- Read at 100 sends: bounce rate (< 5 % or stop and fix the list), spam-folder signal (seed inboxes), opt-outs.
- Judge at 300 per segment: reply ≥ 3 % or signup ≥ 2 % keeps the segment; otherwise change ONE variable (topic record, subject line, or segment) and run the next 100.
- Log per wave in `audit/OUTREACH.md` (dates, counts, replies by shape); recipient-level state stays in `master.csv` (`sent_on`, `replied`, `outcome` columns added at Phase 4).

## What the agent will not do
- Guess, scrape or infer a personal address; every row cites its page.
- Send. The founder sends, or the tool sends on his account after he approves each batch.
- Write a number into the collateral that is not measured.
