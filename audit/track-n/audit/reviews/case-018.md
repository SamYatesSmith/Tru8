# case-018 — Review Sheet

**Claim**: Global sea levels have risen by approximately 8 to 9 inches between the years 1880 and the present.
**Type**: empirical | **Model**: gemini-2.5-flash-lite | **Prompt hash**: `2c6f56bfb7e5`

## Elements

- **e1**: There exists a measurable global average sea level in the year 1880.
- **e2**: There exists a measurable global average sea level in the present day.
- **e3**: The difference between the present-day global average sea level and the global average sea level in 1880 is approximately 8 to 9 inches.

---

## e1 — mapper state: `unresolved`
*Uncertainty*: The evidence discusses sea level rise since 1880 but does not explicitly state that a measurable global average sea level existed in 1880.

### ev-092a45e47bf6 -> `context`

**Sea-Level Rise and the Role of Geneva** (genevaenvironmentnetwork.org, reporting/analysis)
URL: https://www.genevaenvironmentnetwork.org/resources/updates/sea-level-rise-and-the-role-of-geneva/

**Mapper saw** (first 400 chars):
> Even if the world successfully limits global warming to 1. 5°C above pre-industrial levels, the target set by the Paris Agreement, sea levels are still expected to rise significantly. The World Meteorological Organization (WMO) reported that global sea levels reached a record high in 2023, rising about 20–23 cm since 1880. Alarmingly, the rate of rise has more than doubled in the last decade compa

**Beyond window** (+190 chars):
> red to the 1990s. Average sea levels could rise by up to 90 cm by 2100 under worst-case IPCC climate scenarios, and recent research suggests the increase could even surpass these projections

**Mapper reasoning**: —

| Field | Value |
|-------|-------|
| Mapper relationship | `context` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `___` (true/false) |
| Notes | |

### ev-141e79ab9d3f -> `context`

**Which of these actually contributes to rising sea levels?** (scienceupfirst.com, reporting/analysis)
URL: https://scienceupfirst.com/climate/which-of-these-actually-contributes-to-rising-sea-levels/

**Mapper saw** (first 400 chars):
> For thousands of years, sea levels were relatively stable. But around 1850, when we began burning fossil fuels on a large scale, the oceans started to rise – and they haven’t stopped since (6,10,11,12). The global sea level average has already risen 8-9 inches (21–24 cm) since 1880, and the pace is accelerating (6,7,13). 7 mm per year in the early 1900s increased to 1. 5 mm per year in 2023

**Mapper reasoning**: —

| Field | Value |
|-------|-------|
| Mapper relationship | `context` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-e1fc5de57de7 -> `context`

**NOAA Sea Level Rise Data** (NOAA CDO, primary/data)
URL: https://www.climate.gov/news-features/understanding-climate/climate-change-global-sea-level

**Mapper saw** (first 400 chars):
> NOAA's tide gauge and satellite altimetry data shows global mean sea level has risen about 3.4 mm per year since 1993. Long-term records from tide gauges show approximately 8-9 inches of sea level rise since 1880.

**Mapper reasoning**: —

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

### ev-092a45e47bf6 -> `supports`

**Sea-Level Rise and the Role of Geneva** (genevaenvironmentnetwork.org, reporting/analysis)
URL: https://www.genevaenvironmentnetwork.org/resources/updates/sea-level-rise-and-the-role-of-geneva/

**Mapper saw** (first 400 chars):
> Even if the world successfully limits global warming to 1. 5°C above pre-industrial levels, the target set by the Paris Agreement, sea levels are still expected to rise significantly. The World Meteorological Organization (WMO) reported that global sea levels reached a record high in 2023, rising about 20–23 cm since 1880. Alarmingly, the rate of rise has more than doubled in the last decade compa

**Beyond window** (+190 chars):
> red to the 1990s. Average sea levels could rise by up to 90 cm by 2100 under worst-case IPCC climate scenarios, and recent research suggests the increase could even surpass these projections

**Mapper reasoning**: —

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `___` (true/false) |
| Notes | |

### ev-bc81fc106cf5 -> `supports`

**Global sea level rose faster than expected in 2024, according to ...** (abcnews.com, reporting/news_reporting)
URL: https://abcnews.com/International/global-sea-level-rose-faster-expected-2024-nasa/story?id=119795389

**Mapper saw** (first 400 chars):
> "With 2024 as the warmest year on record, Earth’s expanding oceans are following suit, reaching their highest levels in three decades," said Nadya Vinogradova Shiffer, head of physical oceanography programs and the Integrated Earth System Observatory at NASA. The rate of annual sea level rise has more than doubled since the satellite record began in 1993 -- with sea levels rising at least 4 inches

**Beyond window** (+391 chars):
>  since then, according to NASA. Sea levels have risen between 8 inches and 9 inches since 1880, according to the National Oceanic and Atmospheric Administration. Human-amplified climate change is the primary cause for present-day rising sea levels, climate research shows. Heat from the ocean's surface has slowly making its way down into cooler waters deeper into the sea, according to NASA

**Mapper reasoning**: —

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `___` (true/false) |
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

## e3 — mapper state: `supported`

### ev-092a45e47bf6 -> `supports`

**Sea-Level Rise and the Role of Geneva** (genevaenvironmentnetwork.org, reporting/analysis)
URL: https://www.genevaenvironmentnetwork.org/resources/updates/sea-level-rise-and-the-role-of-geneva/

**Mapper saw** (first 400 chars):
> Even if the world successfully limits global warming to 1. 5°C above pre-industrial levels, the target set by the Paris Agreement, sea levels are still expected to rise significantly. The World Meteorological Organization (WMO) reported that global sea levels reached a record high in 2023, rising about 20–23 cm since 1880. Alarmingly, the rate of rise has more than doubled in the last decade compa

**Beyond window** (+190 chars):
> red to the 1990s. Average sea levels could rise by up to 90 cm by 2100 under worst-case IPCC climate scenarios, and recent research suggests the increase could even surpass these projections

**Mapper reasoning**: —

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `___` (true/false) |
| Notes | |

### ev-56473142f329 -> `supports`

**Climate Indicators | NASA Earthdata** (earthdata.nasa.gov, primary/data)
URL: https://www.earthdata.nasa.gov/topics/climate-indicators

**Mapper saw** (first 400 chars):
> Access a range of datasets and data tools to further your climate indicators research. Global sea level has risen eight to nine inches since reliable record keeping began in 1880 and is projected to rise another one to eight feet by 2100. Sea level rise is one of the indicators that describe climate without reducing changes to only temperature. The indicators comprise key information for the most 

**Beyond window** (+120 chars):
> relevant domains of climate: temperature and energy, atmospheric composition, ocean and water, and the frozen cryosphere

**Mapper reasoning**: —

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `___` (true/false) |
| Notes | |

### ev-141e79ab9d3f -> `supports`

**Which of these actually contributes to rising sea levels?** (scienceupfirst.com, reporting/analysis)
URL: https://scienceupfirst.com/climate/which-of-these-actually-contributes-to-rising-sea-levels/

**Mapper saw** (first 400 chars):
> For thousands of years, sea levels were relatively stable. But around 1850, when we began burning fossil fuels on a large scale, the oceans started to rise – and they haven’t stopped since (6,10,11,12). The global sea level average has already risen 8-9 inches (21–24 cm) since 1880, and the pace is accelerating (6,7,13). 7 mm per year in the early 1900s increased to 1. 5 mm per year in 2023

**Mapper reasoning**: —

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-e1fc5de57de7 -> `supports`

**NOAA Sea Level Rise Data** (NOAA CDO, primary/data)
URL: https://www.climate.gov/news-features/understanding-climate/climate-change-global-sea-level

**Mapper saw** (first 400 chars):
> NOAA's tide gauge and satellite altimetry data shows global mean sea level has risen about 3.4 mm per year since 1993. Long-term records from tide gauges show approximately 8-9 inches of sea level rise since 1880.

**Mapper reasoning**: —

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### State judgment: `supported`

Ref tally: 4 supports, 0 challenges, 0 context

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

- **ev-bafad35f38b5**: A Seafloor Spreading Slowdown May Have Slashed Sea Levels (CrossRef)
  > <jats:p>Between 15 million and 6 million years ago, a drop in ocean crust production may have lowered sea level by 26–32 meters.</jats:p>

- **None**: No, coastal peak images don't disprove sea level rise | Fact check (USA Today)
  > Sea level rise detected worldwide, including near Sugarloaf Mountain in Brazil | Fact check The claim: Images of Brazilian rock formation show global 

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
