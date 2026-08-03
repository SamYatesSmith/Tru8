# case-005 — Review Sheet

**Claim**: Electric vehicles constitute 18% of all new car sales globally.
**Type**: empirical | **Model**: gemini-2.5-flash-lite | **Prompt hash**: `89c616093abf`

## Elements

- **e1**: The total number of new cars sold globally is recorded.
- **e2**: The total number of new electric vehicles sold globally is recorded.
- **e3**: The ratio of new electric vehicle sales to total new car sales is calculated.
- **e4**: This calculated ratio is equal to 18%.

---

## e1 — mapper state: `unresolved`
*Uncertainty*: The evidence does not explicitly state that the total number of new cars sold globally is recorded, only that it is implied by the reporting of EV sales percentages.

### ev-rec-e1_2_41cc5938 -> `context`

**European Market Monitor: Cars and Vans (November 2025)** (theicct.org, unclassified/unclassified)
URL: https://theicct.org/publication/european-market-monitor-cars-and-vans-nov-2025/

**Mapper saw** (first 400 chars):
> For year-to-date (YTD) 2025, the BEV share of total new registrations was 18%, which represents an increase of 4 percentage points compared with the same period ...

**Mapper reasoning**: This evidence mentions the BEV share of total new registrations in the context of European markets, implying total new registrations are tracked.

| Field | Value |
|-------|-------|
| Mapper relationship | `context` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-e3_2_780649c4 -> `context`

**Differences in vehicle electrification policies and optimal transition ...** (onlinelibrary.wiley.com, unclassified/unclassified)
URL: https://onlinelibrary.wiley.com/doi/full/10.1111/jiec.70028

**Mapper saw** (first 400 chars):
> Electric vehicles (EVs), including plug-in hybrid vehicles (PHEVs) and battery electric vehicles (BEVs), accounted for 18% of the global new-vehicle sales in ...

**Mapper reasoning**: This evidence states that EVs accounted for 18% of global new-vehicle sales, implying that total new-vehicle sales are recorded.

| Field | Value |
|-------|-------|
| Mapper relationship | `context` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-e3_4_7f815aff -> `context`

**Emissions reduction potential and feasibility of vehicle-to-grid for ...** (sciencedirect.com, unclassified/unclassified)
URL: https://www.sciencedirect.com/science/article/pii/S2666386425002152

**Mapper saw** (first 400 chars):
> In 2023, global EV sales exceed 14 million units—mostly passenger EVs—representing 18% of total car sales, and the average proportion is expected to jump ...

**Mapper reasoning**: This evidence states that global EV sales represented 18% of total car sales in 2023, implying that total car sales are recorded.

| Field | Value |
|-------|-------|
| Mapper relationship | `context` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### State judgment: `unresolved`

Ref tally: 0 supports, 0 challenges, 3 context

| Field | Value |
|-------|-------|
| Mapper state | `unresolved` |
| Correct? | `___` (true/false) |
| Expected state | `___` (supported/disputed/unresolved) |
| Failure mode | `___` (D/—) |
| Notes | |

---

## e2 — mapper state: `supported`

### ev-rec-e1_1_e2fa0b6c -> `supports`

**Global EV Sales Report — BEVs Reach 18% Share in August!** (cleantechnica.com, unclassified/unclassified)
URL: https://cleantechnica.com/2025/10/06/global-ev-sales-report-bevs-reach-18-share-in-august/

**Mapper saw** (first 400 chars):
> There were 1.7 million plugin vehicles registered worldwide in August. Global plugin vehicle registrations were up 14% in August 2025 compared to August 2024.

**Mapper reasoning**: This evidence reports that 1.7 million plugin vehicles were registered worldwide in August, indicating a recording of global EV sales.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-e2_2_34dad788 -> `supports`

**Electric Vehicle Sales Review Q4-2025 | PwC and Strategy** (strategyand.pwc.com, unclassified/unclassified)
URL: https://www.strategyand.pwc.com/de/en/industries/automotive/electric-vehicle-sales-review-q4-2025.html

**Mapper saw** (first 400 chars):
> Global BEV sales surpassed 4 million in Q4 2025 for the first time, with over 20% of vehicles sold globally being BEVs and full-year growth of 30% ...

**Mapper reasoning**: This evidence states that Global BEV sales surpassed 4 million in Q4 2025, confirming that global electric vehicle sales are recorded.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-e3_4_7f815aff -> `supports`

**Emissions reduction potential and feasibility of vehicle-to-grid for ...** (sciencedirect.com, unclassified/unclassified)
URL: https://www.sciencedirect.com/science/article/pii/S2666386425002152

**Mapper saw** (first 400 chars):
> In 2023, global EV sales exceed 14 million units—mostly passenger EVs—representing 18% of total car sales, and the average proportion is expected to jump ...

**Mapper reasoning**: This evidence states that in 2023, global EV sales exceeded 14 million units, confirming that global electric vehicle sales are recorded.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### State judgment: `supported`

Ref tally: 3 supports, 0 challenges, 0 context

| Field | Value |
|-------|-------|
| Mapper state | `supported` |
| Correct? | `___` (true/false) |
| Expected state | `___` (supported/disputed/unresolved) |
| Failure mode | `___` (D/—) |
| Notes | |

---

## e3 — mapper state: `supported`

### ev-rec-e1_2_41cc5938 -> `supports`

**European Market Monitor: Cars and Vans (November 2025)** (theicct.org, unclassified/unclassified)
URL: https://theicct.org/publication/european-market-monitor-cars-and-vans-nov-2025/

**Mapper saw** (first 400 chars):
> For year-to-date (YTD) 2025, the BEV share of total new registrations was 18%, which represents an increase of 4 percentage points compared with the same period ...

**Mapper reasoning**: This evidence states that the BEV share of total new registrations was 18% year-to-date 2025, directly indicating the calculation of this ratio.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-e3_0_890a4b1d -> `supports`

**A high-resolution dataset on electric passenger vehicle ... - Nature** (nature.com, unclassified/unclassified)
URL: https://www.nature.com/articles/s41597-025-05770-7

**Mapper saw** (first 400 chars):
> Also, the global electric passenger vehicle penetration rate achieved 18%, which is expected to exceed 80% by 2040 under net-zero emission targets. Behind such ...

**Mapper reasoning**: This evidence mentions the global electric passenger vehicle penetration rate achieved 18%, which is the ratio of EV sales to total car sales.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-e3_1_f281254c -> `supports`

**[PDF] “Equilibrium Effects in Complementary Markets: Electric Vehicle ...** (tse-fr.eu, unclassified/unclassified)
URL: https://www.tse-fr.eu/sites/default/files/TSE/documents/doc/wp/2024/wp_tse_1589.pdf

**Mapper saw** (first 400 chars):
> Electric vehicles. (EVs) now account for more than 20% of global sales (International Energy Agency, 2025). This shift moves the complementary market for ...

**Mapper reasoning**: This evidence states that electric vehicles (EVs) now account for more than 20% of global sales, which is the ratio of EV sales to total sales.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-e3_2_780649c4 -> `supports`

**Differences in vehicle electrification policies and optimal transition ...** (onlinelibrary.wiley.com, unclassified/unclassified)
URL: https://onlinelibrary.wiley.com/doi/full/10.1111/jiec.70028

**Mapper saw** (first 400 chars):
> Electric vehicles (EVs), including plug-in hybrid vehicles (PHEVs) and battery electric vehicles (BEVs), accounted for 18% of the global new-vehicle sales in ...

**Mapper reasoning**: This evidence states that EVs accounted for 18% of the global new-vehicle sales, directly representing the calculated ratio.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-e3_4_7f815aff -> `supports`

**Emissions reduction potential and feasibility of vehicle-to-grid for ...** (sciencedirect.com, unclassified/unclassified)
URL: https://www.sciencedirect.com/science/article/pii/S2666386425002152

**Mapper saw** (first 400 chars):
> In 2023, global EV sales exceed 14 million units—mostly passenger EVs—representing 18% of total car sales, and the average proportion is expected to jump ...

**Mapper reasoning**: This evidence states that global EV sales represented 18% of total car sales in 2023, confirming the calculation of this ratio.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-e1_4_8e16e0b5 -> `context`

**Electric Vehicle Outlook | BloombergNEF** (about.bnef.com, unclassified/unclassified)
URL: https://about.bnef.com/insights/clean-transport/electric-vehicle-outlook/

**Mapper saw** (first 400 chars):
> Global sales of electric vehicles continue to rise and are set to represent one in four cars sold this year. But some markets are experiencing a significant ...

**Mapper reasoning**: This evidence discusses global sales of electric vehicles and their share of cars sold, providing context for the calculation of this ratio.

| Field | Value |
|-------|-------|
| Mapper relationship | `context` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-e3_3_951f63cd -> `context`

**[PDF] autosinnovate.org Alliance for Automotive Innovation Comments on ...** (autosinnovate.org, unclassified/unclassified)
URL: https://www.autosinnovate.org/posts/agency-comments/energy-environment/2025-energy-environment/EPA%20on%20GHG%20Endangerment%20and%20Standards%20Rescission%209-22-2025

**Mapper saw** (first 400 chars):
> Some data sets herein may also include fuel cell electric vehicles, which are only a very small portion of total electric vehicles sales or market share. 15 ...

**Mapper reasoning**: This evidence discusses how different datasets might include or exclude certain types of electric vehicles when calculating market share, providing context for the ratio calculation.

| Field | Value |
|-------|-------|
| Mapper relationship | `context` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### State judgment: `supported`

Ref tally: 5 supports, 0 challenges, 2 context

| Field | Value |
|-------|-------|
| Mapper state | `supported` |
| Correct? | `___` (true/false) |
| Expected state | `___` (supported/disputed/unresolved) |
| Failure mode | `___` (D/—) |
| Notes | |

---

## e4 — mapper state: `supported`

### ev-rpf-0_1 -> `supports`

**Global Electric Vehicle Market Share - Counterpoint Research** (counterpointresearch.com, reporting/data)
URL: https://counterpointresearch.com/en/insights/global-electric-vehicle-market-share-quarterly

**Mapper saw** (first 400 chars):
> BEV penetration reached a new milestone in the quarter, accounting for 18% of global PV sales, up from 14% in the same period last year. China remained the ...

**Mapper reasoning**: States that BEV penetration reached 18% of global PV sales, directly supporting the claim.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rpf-0_3 -> `supports`

**THE 18% MILESTONE! Global EV Sales Explode 40% - YouTube** (youtube.com, reporting/news_reporting)
URL: https://www.youtube.com/watch?v=fhJ8C4qbFcI

**Mapper saw** (first 400 chars):
> THE 18% MILESTONE! Global EV Sales Explode 40%—But China is Dominating Global electric vehicle sales have surged more than 40%, pushing EVs to a historic ...

**Mapper reasoning**: Mentions 'THE 18% MILESTONE!' in relation to global EV sales, supporting the claim.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### State judgment: `supported`

Ref tally: 2 supports, 0 challenges, 0 context

| Field | Value |
|-------|-------|
| Mapper state | `supported` |
| Correct? | `___` (true/false) |
| Expected state | `___` (supported/disputed/unresolved) |
| Failure mode | `___` (D/—) |
| Notes | |

---

## Missing refs

Evidence the mapper should have mapped but didn't:

- **ev-b65537736bac**: Electric car use by country (Wikipedia)
  > Electric car use by country varies worldwide, as the adoption of plug-in electric vehicles is affected by consumer demand, market prices, availability

- **ev-rpf-0_2**: Electric Vehicle Sales Review Q3-2025 | PwC and Strategy (strategyand.pwc.com)
  > Sales in Q3 increased by 36% year-on-year, exceeding two million registrations and resulting in a BEV market share of 34%. The increasing popularity o

- **ev-rpf-0_0**: The rest of the world is lapping the U.S. in the EV race (yaleclimateconnections.org)
  > EVs made up about 25% of global car sales in 2025. In the U.S., they only made up 10%.

Add missing refs here:

| Element | Evidence ID | Expected relationship | Failure mode | Window sufficient? | Notes |
|---------|-------------|----------------------|--------------|-------------------|-------|
| | | | | | |

---

## Failure mode key

- **A**: Missed contradiction
- **B**: Phantom support
- **C**: Misattributed scope
- **D**: State inflation
