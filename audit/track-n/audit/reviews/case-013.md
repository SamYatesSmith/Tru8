# case-013 — Review Sheet

**Claim**: The Amazon rainforest is responsible for producing 20% of the Earth's oxygen.
**Type**: empirical | **Model**: gemini-2.5-flash-lite | **Prompt hash**: `9edd97de5f31`

## Elements

- **e1**: The total amount of oxygen produced by the Amazon rainforest can be quantified.
- **e2**: The total amount of oxygen produced by all sources globally can be quantified.
- **e3**: The ratio of oxygen produced by the Amazon rainforest to global oxygen production is 20%.

---

## e1 — mapper state: `unresolved`

### ev-f88e50b2eed0 -> `context`

**Amazon Doesn’t Produce 20% of Earth’s Oxygen** (FactCheck.org, reporting/opinion)
URL: https://www.factcheck.org/2019/09/amazon-doesnt-produce-20-of-earths-oxygen/

**Mapper saw** (first 400 chars):
> Q: Does the Amazon produce 20% of the world’s oxygen? A: No. Scientists estimate the percentage is closer to 6 to 9%, and the Amazon ultimately consumes nearly all of that oxygen itself. FULL QUESTION Does the Amazon Rainforest truly produce 20% of the Earth’s oxygen? Where does the remaining 80% come from? FULL ANSWER On Aug. 20, Brazil’s space agency sparked a media frenzy when it released satel

**Beyond window** (+1600 chars):
> lite data showing an alarming number of wildfires in the Amazon rainforest over the past year — nearly 40,000, or a 77% rise compared with the same time period in 2018. Most of the fires have started since June. NASA also has confirmed the surge, declaring 2019 the worst year for wildfires in the region since 2010. Scientists attribute the uptick in fires to increased deforestation, at least some of which, critics say, has been encouraged by Brazil’s president, Jair Bolsonaro. As news outlets ac...

**Mapper reasoning**: Discusses the percentage of oxygen produced by the Amazon, implying it can be quantified.

| Field | Value |
|-------|-------|
| Mapper relationship | `context` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `___` (true/false) |
| Notes | |

### ev-0c8929bec31f -> `context`

**Take a breath: the Amazon does not produce 20% of the world's ...** (AP News, reporting/news_reporting)
URL: https://apnews.com/article/archive-fact-checking-7106380249

**Mapper saw** (first 400 chars):
> Take a breath: the Amazon does not produce 20% of the world’s oxygen CLAIM: The Amazon rainforest _ “the lungs of the Earth” _ produces 20% of the planet’s oxygen. AP’S ASSESSMENT: False. Scientists say while the Amazon is important to the world’s ecosystem, it does not produce 20% of the world’s oxygen. In fact, the region absorbs about the same amount of oxygen it produces. THE FACTS: The 20% fi

**Beyond window** (+1600 chars):
> gure circulated widely this month as concerns grew around fires burning in the Amazon. It was passed on social media platforms, cited by politicians and quoted by the media, including The Associated Press. The reality, according to experts, is that the Amazon produces and consumes oxygen in nearly perfect balance. That’s because while it produces oxygen through photosynthesis, it also absorbs it to grow, as do animals and microbes. “Even if all plants in the Amazon stopped doing photosynthesis, ...

**Mapper reasoning**: Mentions scientists' estimates of oxygen production by the Amazon, implying it can be quantified.

| Field | Value |
|-------|-------|
| Mapper relationship | `context` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `___` (true/false) |
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

## e2 — mapper state: `unresolved`

### ev-f88e50b2eed0 -> `context`

**Amazon Doesn’t Produce 20% of Earth’s Oxygen** (FactCheck.org, reporting/opinion)
URL: https://www.factcheck.org/2019/09/amazon-doesnt-produce-20-of-earths-oxygen/

**Mapper saw** (first 400 chars):
> Q: Does the Amazon produce 20% of the world’s oxygen? A: No. Scientists estimate the percentage is closer to 6 to 9%, and the Amazon ultimately consumes nearly all of that oxygen itself. FULL QUESTION Does the Amazon Rainforest truly produce 20% of the Earth’s oxygen? Where does the remaining 80% come from? FULL ANSWER On Aug. 20, Brazil’s space agency sparked a media frenzy when it released satel

**Beyond window** (+1600 chars):
> lite data showing an alarming number of wildfires in the Amazon rainforest over the past year — nearly 40,000, or a 77% rise compared with the same time period in 2018. Most of the fires have started since June. NASA also has confirmed the surge, declaring 2019 the worst year for wildfires in the region since 2010. Scientists attribute the uptick in fires to increased deforestation, at least some of which, critics say, has been encouraged by Brazil’s president, Jair Bolsonaro. As news outlets ac...

**Mapper reasoning**: Discusses the percentage of oxygen produced by the Amazon in relation to the world's oxygen, implying global production can be quantified.

| Field | Value |
|-------|-------|
| Mapper relationship | `context` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `___` (true/false) |
| Notes | |

### ev-0c8929bec31f -> `context`

**Take a breath: the Amazon does not produce 20% of the world's ...** (AP News, reporting/news_reporting)
URL: https://apnews.com/article/archive-fact-checking-7106380249

**Mapper saw** (first 400 chars):
> Take a breath: the Amazon does not produce 20% of the world’s oxygen CLAIM: The Amazon rainforest _ “the lungs of the Earth” _ produces 20% of the planet’s oxygen. AP’S ASSESSMENT: False. Scientists say while the Amazon is important to the world’s ecosystem, it does not produce 20% of the world’s oxygen. In fact, the region absorbs about the same amount of oxygen it produces. THE FACTS: The 20% fi

**Beyond window** (+1600 chars):
> gure circulated widely this month as concerns grew around fires burning in the Amazon. It was passed on social media platforms, cited by politicians and quoted by the media, including The Associated Press. The reality, according to experts, is that the Amazon produces and consumes oxygen in nearly perfect balance. That’s because while it produces oxygen through photosynthesis, it also absorbs it to grow, as do animals and microbes. “Even if all plants in the Amazon stopped doing photosynthesis, ...

**Mapper reasoning**: Mentions the world's oxygen production in the context of the Amazon's contribution, implying global production can be quantified.

| Field | Value |
|-------|-------|
| Mapper relationship | `context` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `___` (true/false) |
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

## e3 — mapper state: `disputed`

### ev-f88e50b2eed0 -> `challenges`

**Amazon Doesn’t Produce 20% of Earth’s Oxygen** (FactCheck.org, reporting/opinion)
URL: https://www.factcheck.org/2019/09/amazon-doesnt-produce-20-of-earths-oxygen/

**Mapper saw** (first 400 chars):
> Q: Does the Amazon produce 20% of the world’s oxygen? A: No. Scientists estimate the percentage is closer to 6 to 9%, and the Amazon ultimately consumes nearly all of that oxygen itself. FULL QUESTION Does the Amazon Rainforest truly produce 20% of the Earth’s oxygen? Where does the remaining 80% come from? FULL ANSWER On Aug. 20, Brazil’s space agency sparked a media frenzy when it released satel

**Beyond window** (+1600 chars):
> lite data showing an alarming number of wildfires in the Amazon rainforest over the past year — nearly 40,000, or a 77% rise compared with the same time period in 2018. Most of the fires have started since June. NASA also has confirmed the surge, declaring 2019 the worst year for wildfires in the region since 2010. Scientists attribute the uptick in fires to increased deforestation, at least some of which, critics say, has been encouraged by Brazil’s president, Jair Bolsonaro. As news outlets ac...

**Mapper reasoning**: States the percentage is closer to 6 to 9%, directly contradicting the claimed 20%.

| Field | Value |
|-------|-------|
| Mapper relationship | `challenges` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `___` (true/false) |
| Notes | |

### ev-0c8929bec31f -> `challenges`

**Take a breath: the Amazon does not produce 20% of the world's ...** (AP News, reporting/news_reporting)
URL: https://apnews.com/article/archive-fact-checking-7106380249

**Mapper saw** (first 400 chars):
> Take a breath: the Amazon does not produce 20% of the world’s oxygen CLAIM: The Amazon rainforest _ “the lungs of the Earth” _ produces 20% of the planet’s oxygen. AP’S ASSESSMENT: False. Scientists say while the Amazon is important to the world’s ecosystem, it does not produce 20% of the world’s oxygen. In fact, the region absorbs about the same amount of oxygen it produces. THE FACTS: The 20% fi

**Beyond window** (+1600 chars):
> gure circulated widely this month as concerns grew around fires burning in the Amazon. It was passed on social media platforms, cited by politicians and quoted by the media, including The Associated Press. The reality, according to experts, is that the Amazon produces and consumes oxygen in nearly perfect balance. That’s because while it produces oxygen through photosynthesis, it also absorbs it to grow, as do animals and microbes. “Even if all plants in the Amazon stopped doing photosynthesis, ...

**Mapper reasoning**: Explicitly states the claim that the Amazon produces 20% of the world's oxygen is false.

| Field | Value |
|-------|-------|
| Mapper relationship | `challenges` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `___` (true/false) |
| Notes | |

### State judgment: `disputed`

Ref tally: 0 supports, 2 challenges, 0 context

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

- **ev-581c195a626a**: Amazon fires are destructive, but they aren't depleting Earth's ... (The Conversation)
  > Fires in the Amazon rainforest have captured attention worldwide in August. Brazilian President Jair Bolsonaro, who took office in 2019, pledged in hi

- **ev-db2795227ae9**: Challenges in Sustainable Territorial Management in the Brazilian Amazon Region for the XXI Century (CrossRef)
  > Academic research: Challenges in Sustainable Territorial Management in the Brazilian Amazon Region for the XXI Century

- **ev-0b1da108c976**: Access and the Quality of Drinking Water in Quilombola Communities in the Amazon, the World's Largest Tropical Rainforest (CrossRef)
  > Academic research: Access and the Quality of Drinking Water in Quilombola Communities in the Amazon, the World's Largest Tropical Rainforest

- **ev-32a32c19dadf**: A Conceptual Alternative for Applying Conservation Banking to Offset Development Impacts in the Brazilian Amazon (CrossRef)
  > Academic research: A Conceptual Alternative for Applying Conservation Banking to Offset Development Impacts in the Brazilian Amazon

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
