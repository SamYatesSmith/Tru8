# case-007 — Review Sheet

**Claim**: Deforestation in the Amazon has decreased by 50% compared to the level in 2004.
**Type**: empirical | **Model**: gemini-2.5-flash-lite | **Prompt hash**: `d4cd8af9b3ac`

## Elements

- **e1**: The rate of deforestation in the Amazon in the year 2004 can be quantified.
- **e2**: The current rate of deforestation in the Amazon can be quantified.
- **e3**: The current rate of deforestation is 50% lower than the rate in 2004.

---

## e1 — mapper state: `supported`

### ev-rec-3_2_8b0804d0 -> `supports`

**When the River Runs Dry: How Amazon Deforestation Threatens the ...** (climatepolicyinitiative.org, primary/analysis)
URL: https://www.climatepolicyinitiative.org/publication/when-the-river-runs-dry-how-amazon-deforestation-threatens-the-brazilian-economy/

**Mapper saw** (first 400 chars):
> In 2023, the drought in the Amazon reduced the volume of grain ... Between 2004 and 2014, the deforestation rate was reduced by approximately five times.

**Mapper reasoning**: States that between 2004 and 2014, the deforestation rate was reduced by approximately five times, implying the 2004 rate is a quantifiable baseline.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-3_0_ac5de883 -> `context`

**Amazon deforestation: Drivers, damages, and policies - ScienceDirect** (sciencedirect.com, primary/academic)
URL: https://www.sciencedirect.com/science/article/pii/S0264837725003448

**Mapper saw** (first 400 chars):
> This review discusses the economic drivers, the environmental damages, and the policies enacted to fight Amazon deforestation. It provides key statistics ...

**Mapper reasoning**: Mentions that the review provides key statistics on Amazon deforestation, suggesting rates can be quantified.

| Field | Value |
|-------|-------|
| Mapper relationship | `context` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-e1_4_bde0f2af -> `supports`

**[PDF] Analyzing and forecasting the morphology of Amazon deforestation** (repositorio.usp.br, unclassified/unclassified)
URL: https://repositorio.usp.br/directbitstream/5c11f208-9973-4635-a321-48e8ba2f807c/1-s2.0-S0378112725001707-main.pdf

**Mapper saw** (first 400 chars):
> This study analyzes spatial–temporal deforestation patterns in Amazonas using 36 years of land use and land cover changes .

**Mapper reasoning**: This study analyzes spatial-temporal deforestation patterns in Amazonas using 36 years of land use and land cover changes, which would include quantifying the rate in 2004.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### State judgment: `supported`

Ref tally: 2 supports, 0 challenges, 1 context

| Field | Value |
|-------|-------|
| Mapper state | `supported` |
| Correct? | `___` (true/false) |
| Expected state | `___` (supported/disputed/unresolved) |
| Failure mode | `___` (D/—) |
| Notes | |

---

## e2 — mapper state: `supported`

### ev-rec-3_1_5a6e5f52 -> `context`

**Fires Drove Record-breaking Tropical Forest Loss in 2024** (gfr.wri.org, reporting/news_reporting)
URL: https://gfr.wri.org/latest-analysis-deforestation-trends

**Mapper saw** (first 400 chars):
> The Amazon biome experienced the most loss since a record high in 2016, jumping 110% from 2023 to 2024. 60% of it was due to fires. Agricultural expansion is a ...

**Mapper reasoning**: Mentions loss from 2023 to 2024, indicating current deforestation rates can be quantified.

| Field | Value |
|-------|-------|
| Mapper relationship | `context` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-3_5_24757032 -> `context`

**Observed shifts in regional climate linked to Amazon ...** (nature.com, primary/academic)
URL: https://www.nature.com/articles/s43247-025-02900-2

**Mapper saw** (first 400 chars):
> Our findings show compelling evidence that forest loss has contributed to shift climate toward higher land surface temperatures, lower evapotranspiration, lower ...

**Mapper reasoning**: Discusses observed shifts in climate linked to forest loss, implying current deforestation rates are tracked.

| Field | Value |
|-------|-------|
| Mapper relationship | `context` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-e2_2_bb295be2 -> `supports`

**Recent Forest Loss in the Brazilian Amazon Causes Substantial ...** (agupubs.onlinelibrary.wiley.com, unclassified/unclassified)
URL: https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2025AV001670

**Mapper saw** (first 400 chars):
> Regional average forest cover decreases by an average of 3.2% over this period, closely matching the deforestation rate reported by the PRODES (Figure S2 in ...

**Mapper reasoning**: This evidence reports regional average forest cover decreases by an average of 3.2% over a period and mentions matching the deforestation rate reported by PRODES, indicating a quantifiable current rate.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### State judgment: `supported`

Ref tally: 1 supports, 0 challenges, 2 context

| Field | Value |
|-------|-------|
| Mapper state | `supported` |
| Correct? | `___` (true/false) |
| Expected state | `___` (supported/disputed/unresolved) |
| Failure mode | `___` (D/—) |
| Notes | |

---

## e3 — mapper state: `disputed`
*Uncertainty*: One piece of evidence suggests a reduction of approximately five times (around 80%) between 2004 and 2014, which contradicts the claim of a 50% decrease.

### ev-rec-3_2_8b0804d0 -> `supports`

**When the River Runs Dry: How Amazon Deforestation Threatens the ...** (climatepolicyinitiative.org, primary/analysis)
URL: https://www.climatepolicyinitiative.org/publication/when-the-river-runs-dry-how-amazon-deforestation-threatens-the-brazilian-economy/

**Mapper saw** (first 400 chars):
> In 2023, the drought in the Amazon reduced the volume of grain ... Between 2004 and 2014, the deforestation rate was reduced by approximately five times.

**Mapper reasoning**: States that between 2004 and 2014, the deforestation rate was reduced by approximately five times, which is a reduction of about 80%, not 50%.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### State judgment: `disputed`

Ref tally: 1 supports, 0 challenges, 0 context

| Field | Value |
|-------|-------|
| Mapper state | `disputed` |
| Correct? | `___` (true/false) |
| Expected state | `___` (supported/disputed/unresolved) |
| Failure mode | `___` (D/—) |
| Notes | |

---

## Missing refs

Evidence the mapper should have mapped but didn't:

- **ev-rec-3_6_d319b0f8**: “Vulnerabilities and compound risks of escalating climate disasters ... (nature.com)
  > The Brazilian Amazon is severely impacted by extreme climate events, with 1.8 million people (6.4% of the Brazilian Amazon's population) affected by .

- **ev-rec-3_4_fce7014f**: How climate change and deforestation interact in the transformation ... (nature.com)
  > Here, we quantify the relative contributions of deforestation and global climate change to observed shifts in key Amazonian climate parameters. We ana

- **ev-rec-3_7_79022512**: Impact of Amazonian deforestation on precipitation reverses ... (nature.com)
  > Here we show reversed precipitation responses to Amazon deforestation across wet and dry seasons. During the wet season, deforested grids experienced 

- **ev-rec-3_3_9ddc95bf**: Amazon dieback beyond the 21st century under high-emission ... (nature.com)
  > The Amazon rainforest, the world's largest tropical forest, plays a crucial role in climate regulation but faces risks of dieback under climate change

- **ev-rec-e1_1_41ffad33**: (PDF) The global deforestation footprint of agriculture and forestry (researchgate.net)
  > For example, 86% of global deforestation occurring between 2001 and 2022 can be attributed to crop and cattle production. Footprinting of commodity-li

- **ev-rec-e1_2_1efb0496**: The impact of Amazon deforestation is magnified by changing the ... (cambridge.org)
  > Overall, natural vegetation cover declined from 90.9% to 62.7% between 1986 and 2020, and fragmentation greatly increased, generating 78 000 forest fr

- **ev-rec-e1_3_74345907**: Water Surface Loss and Deforestation in the Brazilian Amazon ... (mdpi.com)
  > The study examines the relationship between water surface loss and deforestation in the Brazilian Amazon, focusing on the expansion of farming (crops 

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
