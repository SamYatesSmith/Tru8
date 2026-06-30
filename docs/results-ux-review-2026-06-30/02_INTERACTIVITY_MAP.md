# Results surface — interactivity & links map (don't-lose-anything)

> 2026-06-30 · Code-grounded inventory of every interactive element, deep-link, and analytics event across the signed-in results surface + six lens views. Source of truth for the redesign's hard rule: **maintain ALL current interactivity + QOL, then improve.** Anything not on this list cannot be silently dropped.

## Deep-link / URL state (MUST survive the redesign)
| Param | Read | Write | Purpose |
|---|---|---|---|
| `?claim=N` | (set via focus) | check-detail-client `:115,:132` | focused claim |
| `?view=LENS` | check-detail `:68`; public-report `:31` | check-detail `:118-120`; public-report `:44-46,:310` | active lens (omitted when default `librarian`) |
| `?rel=REL[,REL]` | check-detail `:177`; public-report `:145` | check-detail `:185-186`; public-report `:152-153` | Evidence filtered to supports/challenges/context (from summary state-count click) |
| `?element=ID` | check-detail `:177`; public-report `:146` | check-detail `:187-188`; public-report `:154-155` | focus a single element in Evidence (disputed-count click) |
| `?fresh=true` | check-detail `:43` | cleared `:85` | force brief processing view post-submit |
| `?upgrade=sources` | check-detail `:221` | (external) | sources-limit upgrade modal |

## Analytics events (MUST keep firing — funnel depends on them)
`report_viewed` (check-detail `:97`, public-report `:57`) · `view_opened` (ViewSelector `:50`, ClaimSummaryPanel `:164` — note `source:'summary'` + `rel`) · `evidence_expanded` (LibrarianView `:220`) · `receipt_opened` (RetrievalFunnel `:110`) · `share_clicked` (share-section `:38,:52,:66`; public-report `:104,:112`) · `export_clicked` (public-report `:121`) · `paywall_hit`/`upgrade_click` (upgrade-modal).

## Shell
Claim grid (`ClaimSectionStack`/`ClaimOverviewCard` — click + keyboard Enter) · prev/next claim (`check-detail-client:145-155,:474-491`) · claim focus + scroll-into-view (`:126-141`) · keyboard arrow-key claim paging (`:158-167`; public `:73-87`) · metadata card · evidence meta strip · progress view (display) · claim-selection (toggle/selectAll/clearAll/submit + Space/Enter) · share section · nav section · error state.

## ClaimSummaryPanel (→ becomes the digest; preserve every link)
State-count chips → filtered Evidence: supports→`go('librarian',{rel:['supports']})`, disputed→challenges (+ element focus if single), contextual→context, gap→`seeker` (`:206-251`) · Metric links Elements→Correspondent, Sources/tier→Librarian (`:262-281`) · Gaps list + "Open Gaps" (`:284-308`) · Explore rail = all six lenses (`:314-333`).

## ViewSelector (→ becomes the segmented switcher)
6 tabs `:40-86`, `view_opened` on change, disabled-tooltip for Seeker at overview `:78-82`, `?view=` sync. `ALL_TABS` order/labels/subtitles `:25-32`.

## The six lens views — internal controls to preserve
- **Librarian (Evidence):** heatmap cells (dual tier+type filter) · FilterPills tier×3/type×6/relationship×3 + Clear all (`FilterPills:45-94`) · element-focus badge + clear (`:255-269`) · diagnostic toggle (conditional on variance, `:272-286`) · ReadingTable (close + Visit source + Archive) · EvidenceLedger + SortControl (date/source/element) · LedgerCard expand + archived link · RetrievalFunnel receipts disclosure.
- **Correspondent (Sources):** domain expand/collapse (`expandedDomain`) · SourceGaps callouts (no-primary, sole-source).
- **Chronologist (Timeline):** node click → expand detail (`:101-107`) · desktop force map vs mobile timeline · undated sidebar.
- **Seeker (Gaps):** coverage map · UnknownElementCard + evidence-ref chips · **BountyField** (editable research brief) · **ResearchButton** (re-search: startGapResearch + 2.5s poll + status messages + onComplete→refresh, `:60-143`) · resolved-elements collapse (`:192-200`) · ExplorePanel related-claim cards.
- **Cartographer (Map):** D3 force EvidenceMap — node hover/select, element-column hover, ResizeObserver (`:170-250`) · `onSwitchToLibrarian` trigger · mobile ElementRoster expand.
- **Projectionist (Video):** VideoCard = full-card `<a>` new-tab + play/duration overlays · tab hidden when 0 videos (`check-detail:501`).

## Subtle / easy-to-miss affordances (HIGH risk of accidental drop)
1. **Hover-only arrows** on summary chips, Explore rail, MetricLinks (opacity-0→100). 2. **Keyboard:** arrow-key claim paging; Space/Enter on selection cards. 3. **Heatmap cell = dual-axis filter** (sets tier AND type at once). 4. **Conditional controls that vanish:** Projectionist tab (no videos), diagnostic toggle (no variance), element-focus badge (after clear), resolved-collapse (no resolved). 5. **`?rel=`/`?element=` arrive from summary but aren't reflected in the FilterPills UI** — user may not see why Evidence is filtered (a real QOL gap to fix). 6. **Programmatic scroll-into-view** on claim/lens change (can be missed). 7. **Evidence filter silently cleared on claim change.**

---

## Implications for the redesign

**MAINTAIN (carry forward verbatim into the digest + segmented switcher):**
- Every summary→lens deep-link (the digest already does this in the sandbox — the bar bands, key-findings, strongest-support/challenge, gaps map onto the existing `go(view,{rel,element})` calls). The sandbox's click-to-filter IS this mechanism re-skinned.
- All six lenses' internal controls untouched (the redesign changes the *entry + switcher*, not each lens's body in v1).
- All `?view=/?claim=/?rel=/?element=` params + all analytics events.

**IMPROVE (QOL wins this map surfaces):**
1. **Reflect `?rel=`/`?element=` in the Evidence filter UI** — today a summary click filters Evidence but the FilterPills don't show why (#5 above). The digest's "Showing N challenges · clear" pill (already in the sandbox) fixes exactly this.
2. **Promote hover-only arrows to always-visible affordances** (ties to the clickability fixes).
3. **Make conditional-control disappearance less surprising** (e.g. keep the Projectionist slot or label why it's absent).
4. **Surface keyboard paging** (currently invisible).
5. **Segmented switcher** replaces the ghost ViewSelector — same `onTabChange`/`?view=` contract, better signifiers + default + question labels.

**Net:** the redesign is additive at the entry layer (digest + switcher) over an interaction graph that is already rich and already deep-linked. The digest reuses the exact `go(view, {rel, element})` navigation contract — so "maintain interactivity" is largely free, and the QOL wins are concentrated in *making the existing affordances visible and legible*.
