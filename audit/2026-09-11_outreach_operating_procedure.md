# Outreach operating procedure — tailored at volume, every record read

**Status:** ACTIVE from 2026-09-11 (founder decisions taken this morning; supersedes the
"no automation, no templates, no volume" rule in `OUTREACH.md` and the 300-send
sequencer motion in `2026-09-10_outreach_volume_plan.md` §3–§7 until the wave-1 verdict).
**Owner:** founder. **Operator:** the agent, inside a 6-hour session per working day.
**Data:** `audit/recipients/queue.csv` (gitignored, built by
`backend/scripts/outreach_queue.py` from `master.csv`; it is the working file — the state
of every recipient lives there and nowhere else).

---

## 0. The decisions this procedure rests on (founder, 2026-09-11)

| Decision | Answer |
|---|---|
| Bespoke vs volume | **Neither. Tailored at volume.** Automate the tailoring (record + draft), never the message. Every record is read by the founder before it is sent. |
| Segments for wave 1 | Journalists (UK) + newsletter writers. OSINT rows ride along. Legal / comms / think-tank / dev segments wait for the wave-1 verdict. |
| List route | The 667 rows already collected. No Apollo, no media database. |
| Records | Run through the **API route** (`tru8_check`, full tier, `max_age_hours=0`, 15p agent price / ~1.2p real) under the founder's key, so every record sits in his account and carries a public `/r/` link. |
| Sending | By hand from the founder's mailbox and accounts. No sequencer for wave 1. A separate sending subdomain + mailbox is the only purchase (~£5–10/month), set up now so it warms while wave 1 runs. |
| Budget | Ceiling £750–£1,000. Wave 0–1 spend: under £20 plus check money. Usability study (~£200) and one niche-newsletter slot (~£100–300) only after the wave-1 verdict. |
| Verdict | Read at **50 sends** against the table in `OUTREACH.md`. Sending does not pause for it; replies take a week. |
| Time | 6+ hours per session, Fri 11 Sep, then Mon 14 – Fri 18 Sep. Weekend off. |

## 1. Five rules that never bend

1. **Every record is read by the founder before it is sent.** Send it whatever it shows —
   invariant #7 holds at the distribution layer.
2. **Every note is about a claim the recipient is working on now,** cites one specific thing
   visible on the rendered record, and is written for the route it travels by.
3. **No route we did not see on a public page; no personal mailbox; no guessed address.**
   Enforced by `merge_recipients.py`, re-checked at send time for review-flagged rows.
4. **Every sentence in a note is traceable** to the rendered record, the recipient's page, or
   a verified product fact. A second, fresh pass checks this before the founder reads.
5. **Nothing external is sent by the agent.** The founder sends; the agent prepares.

## 2. Who does what

| Step | Agent | Founder |
|---|---|---|
| Choose the day's batch from the queue | ✔ proposes 20–30 rows | approves or swaps |
| Verify the recipient's current topic (fetch their latest piece, confirm date, byline, claim) | ✔ | — |
| Run the record (API, full tier) and store the full check id | ✔ | — |
| Pressure pass (page, every lens, PDF) and grade | ✔ | — |
| Draft the note for the route | ✔ | — |
| Fact-check pass on the note (fresh context, different agent) | ✔ | — |
| Read the record and the note; approve / edit / reject | — | ✔ (~3 min each) |
| Send, by the route on the row, at the row's day/time | — | ✔ |
| Log `sent_on`, `sent_by_route` | ✔ from founder's word | says what went |
| Reply triage and reply drafts | ✔ drafts | ✔ sends |
| Weekly numbers | ✔ | reads |

## 3. Recipient states (the `status` column)

`queued → topic_verified → record_run → pressure_passed → note_drafted → note_verified →
founder_read → sent → replied → outcome`, plus `held` (with `held_reason`), `rejected`
(founder), `suppressed` (opt-out, bounce, personal contact, or one of the five bespoke targets).
A row moves forward only; a failed step writes `held` with the reason.

## 4. Standards

### 4A. Recipient row — sendable only if
- `route_seen_at_url` is a public page we fetched; `route_type` not a personal mailbox.
- `review_flags` empty, **or** the founder has eyeballed the row (`founder_row_ok` = date).
- `current_topic` carries a date within **30 days** for journalists, **60 days** for
  newsletter writers (their cadence is slower). Older rows are re-verified, not sent.
- `send_channel_how` says physically how the send happens (email · org inbox · Substack
  reply/DM · Bluesky DM · X DM · contact form · comment · LinkedIn message).
- Not on the suppression list; not one of the five bespoke recipients.

### 4B. Topic verification (before any money is spent)
- Fetch the recipient's latest piece; record `topic_source_url`, `topic_piece_date`,
  `topic_claim` (the claim **in their words**, one sentence, no valence added).
- The claim must be **checkable** (a factual proposition, not "covers health").
- If their piece is itself a rebuttal, the record must find it (§4C) or the row is `held`
  with `rebuttal_missed` — never send a record to a disputant whose rebuttal it missed.

### 4C. Record — pressure pass, every record, before a note is drafted
Method is the 2026-09-04 one: public payload
(`/api/v1/checks/public/<id>?detailed=true`), PDF text, and a Playwright DOM dump of `/r/`
on every lens (`?view=librarian|seeker|cartographer|chronologist`).
- Check completed; full id recorded at the moment it is run.
- The claim run is the recipient's claim, verbatim or near; extraction did not drop a conjunct.
- Element states, NOTE lines and badges read as a stranger would: no verdict language, no
  raw ids, no empty cards, unresolved cards render.
- Is the recipient's own piece in the pool? Where is it filed (tier/type/relationship)?
  Record `own_piece_in_pool` = yes/no and its filing. If it is filed in a way that would
  embarrass the recipient (their factcheck as OPINION at weight 1), grade down and say so
  in the note or hold.
- Echo / thin-sourcing / same-study flags: what fired, what the page shows.
- Grade A–C; **C or below is `held`**, never sent. Record `record_grade`, `pressure_pass_on`.
- Cost and time noted from `_meta` (chargedPence, seconds).

### 4D. Note — drafting standard
- **Drafted from the rendered page**, never the payload or the grading notes. Cite only what
  the recipient will see on the surface they will open (web page first; PDF only if named
  as "in the downloadable PDF").
- Structure, ≤ 150 words for email/DM, ≤ 80 for a public comment: their piece + claim in
  one line · what Tru8 is in one clause ("an evidence-research tool I've built — it
  organises sources by tier and type and maps each to the checkable parts of a claim,
  rather than issuing a verdict") · **one specific finding from the record** · **one honest
  seam** (what the record missed or filed oddly) · the link with `?src=<tag>` ·
  one Mom-Test question · sign-off with real name and trueight.com.
- Route-specific: email carries a one-line opt-out and the postal/contact line (PECR);
  DMs carry nothing to unsubscribe from; a comment is public and must read as a reader's
  note, not a pitch.
- Forbidden: "fact-check", "verify", "accurate", "trusted by", any accuracy number, any
  partisan framing ("ammunition"), "every source", "maps every".
- Titles verified (Dr / Prof / editor role) from the recipient's page. Two recipients at
  the same outlet get notes that do not read as templated, on different days.
- UK English.

### 4E. Fact-check pass on the note (a different agent, fresh context)
Inputs: the note, the record URL, the recipient's page URL. Checks, sentence by sentence:
1. Every factual statement about the record is visible on the rendered page (or PDF where
   the note says so).
2. Every statement about the recipient (name, title, outlet, piece title, date, what the
   piece argues) matches their page.
3. The note describes the record it links to (id in the link = id pressure-passed).
4. Forbidden words absent; opt-out line present on email.
5. Word count and route fit.
Output: `note_verified_on` + a one-line verdict, or `held` with the failing sentence quoted.

### 4F. Send standard (founder)
- Read the record page as the recipient will (phone if the route is a DM), then the note.
- Send at the row's `approach_day` / `approach_time_local`, by `send_channel_how`.
- Tell the agent what went; the row gets `sent_on`, `sent_by_route` the same session.
- Never batch two notes to one office inbox on the same day.

### 4G. Approach day and time — defaults the queue builder applies
| Route | Days | Time (recipient local) | Why |
|---|---|---|---|
| email / org_inbox / press_office (UK/IE) | Tue–Thu preferred; Mon, Fri allowed | 09:30–11:00 | before the news-list meeting cycle ends, after the inbox purge |
| email (US) | Tue–Thu | 09:00–10:30 local = 14:00–15:30 UK | same logic, their morning |
| substack reply / DM | Mon–Thu | 12:00–14:00 | writers read replies around lunch |
| bluesky / x DM | Mon–Thu | 12:00–14:00 or 17:00–18:30 | DMs are read between tasks |
| contact_form | Mon–Thu | 10:00–12:00 | office triage in the morning |
| comment on a post | within 3 days of the post, any weekday | 10:00–12:00 | comments are read while the post is live |
| linkedin | Tue–Thu | 08:30–09:30 | first-session reading |
Daily cap **25 sends**, no more than **2 to the same organisation** per day. Fridays after 14:00 and weekends: nothing.

### 4H. Replies
- Reply within the day. Mom-Test questions, never a pitch. Comp on a bite:
  `railway ssh "python -m scripts.grant_checks --email <them> --checks 10"`.
- Log `replied_on`, `reply_shape` (curious / sceptical / how-much / does-it-do-X / not-for-me
  / opt-out), `outcome` (said-useful / ran-own-check / signed-up / no).
- Opt-out → `suppressed` the same hour; the suppression list is the queue's `status`.

## 5. The daily session (6 hours)

| Block | Time | What |
|---|---|---|
| 1 | 0:00–0:20 | Replies triage; log yesterday's sends from the founder's word; numbers line |
| 2 | 0:20–1:00 | Pick tomorrow's batch (20–30 rows) from the queue by priority; founder approves |
| 3 | 1:00–2:45 | Agent: topic verification → records (API) → pressure pass → notes → fact-check pass. Runs in parallel; ask before the batch's spend (~25 × 15p agent price = £3.75 nominal, ~30p real) |
| 4 | 2:45–5:15 | Founder reads records + notes (~3 min each); approves / edits / rejects; agent applies edits |
| 5 | 5:15–6:00 | Founder sends today's approved rows at their times (some fall the next morning — the row says); agent logs; queue rebuilt |

The batch prepared in block 3 is normally sent the **next** working day, so the founder is
always reading today what goes tomorrow. Wave 0 (the five bespoke notes) is the exception:
today.

## 6. Schedule

| Day | Wave | Sends | Also |
|---|---|---|---|
| Fri 11 Sep | 0 | the five bespoke notes, re-run on the live build and re-verified (procedure §4C–4E), sent by the founder by hand | subdomain + mailbox created; founder eyeballs the 55 flagged rows; batch 1 prepared |
| Mon 14 | 1 | ≤25 | batch 2 prepared |
| Tue 15 | 1 | ≤25 → wave 1 reaches 50 | batch 3 prepared |
| Wed 16 | 2 | ≤25 | first wave-1 replies read; nothing changes yet |
| Thu 17 | 2 | ≤25 | |
| Fri 18 | 2 | ≤25 before 14:00 | weekly numbers; wave-1 read (replies so far) |
| Mon 21 | — | — | **wave-1 verdict** at 50 sends + one week: the `OUTREACH.md` table decides the next segment and any purchase |

## 7. The queue file — `audit/recipients/queue.csv`

Built by `python backend/scripts/outreach_queue.py` (idempotent: re-running preserves every
state column already filled; new master rows are appended; priorities and day/time are
recomputed only for rows still `queued`).

Columns, in order:

| Group | Columns |
|---|---|
| identity (from master) | `rid` (stable hash of route) · `segment` · `name` · `role` · `organisation` · `country` · `route_type` · `route` · `route_seen_at_url` · `current_topic` · `notes` · `collected_on` · `review_flags` |
| planning | `priority` (0–100) · `wave` · `approach_day` (ISO date) · `approach_time_local` · `send_channel_how` · `src_tag` |
| topic | `topic_claim` · `topic_source_url` · `topic_piece_date` · `topic_verified_on` |
| record | `check_id` · `record_url` · `record_grade` · `own_piece_in_pool` · `pressure_pass_on` · `charged_pence` |
| note | `note_path` · `note_verified_on` · `founder_row_ok` · `founder_read_on` |
| send | `sent_on` · `sent_by_route` · `replied_on` · `reply_shape` · `outcome` |
| state | `status` · `held_reason` · `updated_on` |

Priority = segment weight (journalists_uk 40 · newsletters 40 · osint 30 · others 10)
+ route weight (email 25 · org_inbox/press_office 18 · substack 16 · bluesky 14 ·
contact_form 10 · x 8 · linkedin 6 · submission_form/github 0)
+ topic freshness (dated ≤14 days 25 · ≤30 days 15 · ≤60 days 8 · undated 0)
− review flag 15. Country: UK/IE first in wave 1; US rows take the afternoon slots.

## 8. Measurement

Weekly, Mondays, one line in `OUTREACH.md`: **sent · replied · said-useful · ran-own-check ·
signed-up (by `src` tag: `python -m scripts.signup_sources`)** · opt-outs · bounces.
Verdict at 50 sends per the `OUTREACH.md` table. Per-recipient truth is the queue file.

## 9. Cost

| Item | Unit | Wave 0–1 |
|---|---|---|
| Record (API, full) | 15p agent price / ~1.2p real | 55 records ≈ £8.25 nominal, ~66p real |
| Fact-check pass | ~1p | ~55p |
| Subdomain mailbox | £5–10/month | one month |
| Total | | **under £20** |

## 10. What this procedure does not do
- No sequencer, no templated sends, no sponsorship, no database subscription, no ads
  before the wave-1 verdict.
- No pipeline work. A record that fails §4C is held; the reason is logged in `OPEN_WORK.md`
  as a product observation, not built this week.
- No sends from the agent, ever.
