# case-006 — Review Sheet

**Claim**: Approximately 60% of the Amazon rainforest is located within Brazil.
**Type**: empirical | **Model**: gemini-2.5-flash-lite | **Prompt hash**: `92fc10695e55`

## Elements

- **e1**: The total geographical area of the Amazon rainforest can be determined.
- **e2**: The geographical area of the Amazon rainforest located within Brazil can be determined.
- **e3**: The proportion of the Amazon rainforest within Brazil is approximately 60%.

---

## e1 — mapper state: `unresolved`

### ev-rec-2_2_7545b3a7 -> `context`

**Amazon Rainforest: A Natural Gem of Brazil - Craft Travel** (crafttravel.com, commentary/analysis)
URL: https://www.crafttravel.com/blog/amazon-rainforest

**Mapper saw** (first 400 chars):
> Spanning over 3 million square miles, it stretches across nine countries in South America, with the majority (approximately 60%) nestled within the borders of ...

**Mapper reasoning**: States the Amazon spans over 3 million square miles, implying its total area can be determined.

| Field | Value |
|-------|-------|
| Mapper relationship | `context` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-2_4_a6c243a6 -> `context`

**Approximately 60% of all Amazon rainforest is located in Brazil....      ** (facebook.com, commentary/analysis)
URL: https://www.facebook.com/chmubeen.khan.90/posts/approximately-60-of-all-amazon-rainforest-is-located-in-brazil/1608420886815586/

**Mapper saw** (first 400 chars):
> The rainforest in Brazil is 60% of the Amazon Rainforest. Brazil contains 25% of the world's rainforests and the Amazon basin gets 7 feet or more of rain a year ...

**Mapper reasoning**: Mentions the Amazon basin and its rainfall, implying its area is a quantifiable aspect.

| Field | Value |
|-------|-------|
| Mapper relationship | `context` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### State judgment: `unresolved`

Ref tally: 0 supports, 0 challenges, 2 context

| Field | Value |
|-------|-------|
| Mapper state | `unresolved` |
| Correct? | `___` (true/false) |
| Expected state | `___` (supported/disputed/unresolved) |
| Failure mode | `___` (D/—) |
| Notes | |

---

## e2 — mapper state: `supported`

### ev-rec-2_0_46bfbafd -> `supports`

**Amazon Rainforest | Plants, Animals, Climate, & Deforestation** (britannica.com, commentary/analysis)
URL: https://www.britannica.com/place/Amazon-Rainforest

**Mapper saw** (first 400 chars):
> Brazil holds approximately 60 percent of the Amazon within its borders. How many species does the Amazon Rainforest contain? The Amazon Rainforest is the ...

**Mapper reasoning**: Explicitly states Brazil holds approximately 60 percent of the Amazon within its borders.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-2_2_7545b3a7 -> `supports`

**Amazon Rainforest: A Natural Gem of Brazil - Craft Travel** (crafttravel.com, commentary/analysis)
URL: https://www.crafttravel.com/blog/amazon-rainforest

**Mapper saw** (first 400 chars):
> Spanning over 3 million square miles, it stretches across nine countries in South America, with the majority (approximately 60%) nestled within the borders of ...

**Mapper reasoning**: States the majority (approximately 60%) is nestled within the borders of Brazil.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-2_3_4d9f2a2a -> `supports`

**How healthy is the Amazon, the world's largest tropical rainforest?** (lemonde.fr, reporting/news_reporting)
URL: https://www.lemonde.fr/en/environment/article/2025/11/05/how-healthy-is-the-amazon-the-world-s-largest-tropical-rainforest_6747118_114.html

**Mapper saw** (first 400 chars):
> Brazil, which is home to 60% of the Amazon, has lost 17% of its forest cover in under 40 years, according to the study. Where do things stand today? In Brazil ...

**Mapper reasoning**: Mentions Brazil is home to 60% of the Amazon.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-2_4_a6c243a6 -> `supports`

**Approximately 60% of all Amazon rainforest is located in Brazil....      ** (facebook.com, commentary/analysis)
URL: https://www.facebook.com/chmubeen.khan.90/posts/approximately-60-of-all-amazon-rainforest-is-located-in-brazil/1608420886815586/

**Mapper saw** (first 400 chars):
> The rainforest in Brazil is 60% of the Amazon Rainforest. Brazil contains 25% of the world's rainforests and the Amazon basin gets 7 feet or more of rain a year ...

**Mapper reasoning**: States the rainforest in Brazil is 60% of the Amazon Rainforest.

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

## e3 — mapper state: `supported`

### ev-rec-2_0_46bfbafd -> `supports`

**Amazon Rainforest | Plants, Animals, Climate, & Deforestation** (britannica.com, commentary/analysis)
URL: https://www.britannica.com/place/Amazon-Rainforest

**Mapper saw** (first 400 chars):
> Brazil holds approximately 60 percent of the Amazon within its borders. How many species does the Amazon Rainforest contain? The Amazon Rainforest is the ...

**Mapper reasoning**: States Brazil holds approximately 60 percent of the Amazon.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-2_2_7545b3a7 -> `supports`

**Amazon Rainforest: A Natural Gem of Brazil - Craft Travel** (crafttravel.com, commentary/analysis)
URL: https://www.crafttravel.com/blog/amazon-rainforest

**Mapper saw** (first 400 chars):
> Spanning over 3 million square miles, it stretches across nine countries in South America, with the majority (approximately 60%) nestled within the borders of ...

**Mapper reasoning**: States the majority (approximately 60%) is within Brazil's borders.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-2_3_4d9f2a2a -> `supports`

**How healthy is the Amazon, the world's largest tropical rainforest?** (lemonde.fr, reporting/news_reporting)
URL: https://www.lemonde.fr/en/environment/article/2025/11/05/how-healthy-is-the-amazon-the-world-s-largest-tropical-rainforest_6747118_114.html

**Mapper saw** (first 400 chars):
> Brazil, which is home to 60% of the Amazon, has lost 17% of its forest cover in under 40 years, according to the study. Where do things stand today? In Brazil ...

**Mapper reasoning**: Confirms Brazil is home to 60% of the Amazon.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-2_4_a6c243a6 -> `supports`

**Approximately 60% of all Amazon rainforest is located in Brazil....      ** (facebook.com, commentary/analysis)
URL: https://www.facebook.com/chmubeen.khan.90/posts/approximately-60-of-all-amazon-rainforest-is-located-in-brazil/1608420886815586/

**Mapper saw** (first 400 chars):
> The rainforest in Brazil is 60% of the Amazon Rainforest. Brazil contains 25% of the world's rainforests and the Amazon basin gets 7 feet or more of rain a year ...

**Mapper reasoning**: Directly states the rainforest in Brazil is 60% of the Amazon Rainforest.

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

- **ev-rec-2_1_1e46c67f**: Brazil and local communities key to conserving Amazon rainforest (worldwildlife.org)
  > The Brazilian Amazon supports more than 40 million people, contains at least 10% of the world's known species, and contributes to the stability of the

- **ev-rec-2_5_d319b0f8**: “Vulnerabilities and compound risks of escalating climate disasters ... (nature.com)
  > The Brazilian Amazon is severely impacted by extreme climate events, with 1.8 million people (6.4% of the Brazilian Amazon's population) affected by .

- **ev-rec-2_6_fce7014f**: How climate change and deforestation interact in the transformation ... (nature.com)
  > While the Amazon biome extends beyond Brazil's borders, the BLA encompasses the vast majority of its forest area under national jurisdiction and inclu

- **ev-rec-2_7_24757032**: Observed shifts in regional climate linked to Amazon ... (nature.com)
  > Since 1985, the Amazon rainforest has lost approximately 11% (~59 Mha) of its forest cover to anthropogenic land uses (based on data from MapBiomas Am

- **ev-rec-2_8_79022512**: Impact of Amazonian deforestation on precipitation reverses ... (nature.com)
  > The crucial role of nonlocal effects in the deforestation–precipitation relationships over the Amazon is important, as 50–60% of the water vapour cont

- **ev-rec-2_9_bcb8ac55**: The influence of environmental attitudes on urban afforestation in ... (nature.com)
  > ... (Brazilian Atlantic Forest), and Andira inermis (Amazon), accounting for 60% of all trees. The vast majority of species (approximately 70%) are ex

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
