# case-009 — Review Sheet

**Claim**: The Amazon rainforest is responsible for producing 20% of the Earth's oxygen.
**Type**: empirical | **Model**: gemini-2.5-flash-lite | **Prompt hash**: `19a8212629c0`

## Elements

- **e1**: The total oxygen production of the Amazon rainforest can be quantified.
- **e2**: The total oxygen production of the Earth can be quantified.
- **e3**: The ratio of oxygen produced by the Amazon rainforest to the Earth's total oxygen production is 20%.

---

## e1 — mapper state: `supported`

### ev-fbecdcc2008a -> `context`

**Amazon Doesn’t Produce 20% of Earth’s Oxygen** (FactCheck.org, reporting/analysis)
URL: https://www.factcheck.org/2019/09/amazon-doesnt-produce-20-of-earths-oxygen/

**Mapper saw** (first 400 chars):
> Q: Does the Amazon produce 20% of the world’s oxygen? A: No. Scientists estimate the percentage is closer to 6 to 9%, and the Amazon ultimately consumes nearly all of that oxygen itself. FULL QUESTION Does the Amazon Rainforest truly produce 20% of the Earth’s oxygen? Where does the remaining 80% come from? FULL ANSWER On Aug. 20, Brazil’s space agency sparked a media frenzy when it released satel

**Beyond window** (+1598 chars):
> lite data showing an alarming number of wildfires in the Amazon rainforest over the past year — nearly 40,000, or a 77% rise compared with the same time period in 2018. Most of the fires have started since June. NASA also has confirmed the surge, declaring 2019 the worst year for wildfires in the region since 2010. Scientists attribute the uptick in fires to increased deforestation, at least some of which, critics say, has been encouraged by Brazil’s president, Jair Bolsonaro. As news outlets ac...

**Mapper reasoning**: Discusses the percentage of oxygen produced by the Amazon rainforest, implying it can be quantified.

| Field | Value |
|-------|-------|
| Mapper relationship | `context` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `___` (true/false) |
| Notes | |

### ev-7744e79261da -> `context`

**Take a breath: the Amazon does not produce 20% of the world's ...** (AP News, reporting/analysis)
URL: https://apnews.com/article/archive-fact-checking-7106380249

**Mapper saw** (first 400 chars):
> Take a breath: the Amazon does not produce 20% of the world’s oxygen CLAIM: The Amazon rainforest _ “the lungs of the Earth” _ produces 20% of the planet’s oxygen. AP’S ASSESSMENT: False. Scientists say while the Amazon is important to the world’s ecosystem, it does not produce 20% of the world’s oxygen. In fact, the region absorbs about the same amount of oxygen it produces. THE FACTS: The 20% fi

**Beyond window** (+1597 chars):
> gure circulated widely this month as concerns grew around fires burning in the Amazon. It was passed on social media platforms, cited by politicians and quoted by the media, including The Associated Press. The reality, according to experts, is that the Amazon produces and consumes oxygen in nearly perfect balance. That’s because while it produces oxygen through photosynthesis, it also absorbs it to grow, as do animals and microbes. “Even if all plants in the Amazon stopped doing photosynthesis, ...

**Mapper reasoning**: Mentions scientists' estimates of oxygen production, indicating it can be quantified.

| Field | Value |
|-------|-------|
| Mapper relationship | `context` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `___` (true/false) |
| Notes | |

### ev-rec-e1_0_e82d0bd2 -> `supports`

**Amazon Lungs of the Earth: 7 Rainforest Benefits** (farmonaut.com, unclassified/unclassified)
URL: https://farmonaut.com/south-america/amazon-lungs-of-the-earth-7-rainforest-benefits

**Mapper saw** (first 400 chars):
> Through photosynthesis, Amazonian plants absorb CO2 and release oxygen, with the region producing over 20% of the world's atmospheric oxygen. This ongoing cycle ...

**Mapper reasoning**: States that the Amazon region produces over 20% of the world's atmospheric oxygen through photosynthesis.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-e1_1_e5366e7b -> `supports`

**The Amazon rainforest is dying from the bottom up—tree roots are ...** (facebook.com, unclassified/unclassified)
URL: https://www.facebook.com/groups/physicsisfun109/posts/950888284256683/

**Mapper saw** (first 400 chars):
> The Amazon Rainforest provides 20 percent of the world's oxygen, is home to the greatest biodiversity of species on Earth, and is the world's biggest carbon ...

**Mapper reasoning**: Explicitly states that the Amazon Rainforest provides 20 percent of the world's oxygen.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-e1_2_f5ac46cc -> `supports`

**NASA Satellite Measures Saharan Dust Transport to Amazon** (linkedin.com, unclassified/unclassified)
URL: https://www.linkedin.com/posts/william-r-g-3182ba37_nasa-satellite-reveals-how-much-saharan-dust-activity-7383003642485833728-Ve3A

**Mapper saw** (first 400 chars):
> And when the Amazon is alive, it produces oxygen. 20% of the world's oxygen comes from the Amazon, and that oxygen keeps us alive. So yes, our breath is ...

**Mapper reasoning**: Mentions that 20% of the world's oxygen comes from the Amazon.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-e1_3_563f4056 -> `supports`

**Charted: Tropical Forest Loss in 2024** (visualcapitalist.com, unclassified/unclassified)
URL: https://www.visualcapitalist.com/charted-tropical-forest-loss-in-2024/

**Mapper saw** (first 400 chars):
> The Amazon forest alone produces 20% of the world's oxygen, earning it the nickname “the lungs of the planet.” It is also home to over 10% of all known ...

**Mapper reasoning**: Asserts that the Amazon forest alone produces 20% of the world's oxygen.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-e1_4_d31ba035 -> `context`

**Impacts of convection, chemistry, and forest clearing on biogenic ...** (pmc.ncbi.nlm.nih.gov, unclassified/unclassified)
URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC12092753/

**Mapper saw** (first 400 chars):
> The Amazon rainforest is the largest source of biogenic volatile organic compounds (BVOCs) to the atmosphere. To understand the distribution and chemistry ...

**Mapper reasoning**: Discusses the Amazon rainforest as a source of biogenic volatile organic compounds, but does not quantify oxygen production.

| Field | Value |
|-------|-------|
| Mapper relationship | `context` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-e2_1_4ab63237 -> `context`

**World Bank Group's post - Facebook** (facebook.com, unclassified/unclassified)
URL: https://www.facebook.com/worldbank/posts/-the-%F0%9D%90%80%F0%9D%90%A6%F0%9D%90%9A%F0%9D%90%B3%F0%9D%90%A8%F0%9D%90%A7%F0%9D%90%A2%F0%9D%90%9A-spans-67-million-square-kilometers-and-holds-half-of-the-planets-r/1283999727101001/

**Mapper saw** (first 400 chars):
> While it's commonly said that the Amazon produces 20% of the world's oxygen ... For context the Amazon Rainforest would cover roughly 60% of the total United ...

**Mapper reasoning**: Acknowledges the common statement that the Amazon produces 20% of the world's oxygen but does not quantify it, instead providing context about the Amazon's land coverage.

| Field | Value |
|-------|-------|
| Mapper relationship | `context` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### State judgment: `supported`

Ref tally: 4 supports, 0 challenges, 4 context

| Field | Value |
|-------|-------|
| Mapper state | `supported` |
| Correct? | `___` (true/false) |
| Expected state | `___` (supported/disputed/unresolved) |
| Failure mode | `___` (D/—) |
| Notes | |

---

## e2 — mapper state: `unresolved`
*Uncertainty*: The provided evidence does not quantify the total oxygen production of the Earth.

### ev-fbecdcc2008a -> `context`

**Amazon Doesn’t Produce 20% of Earth’s Oxygen** (FactCheck.org, reporting/analysis)
URL: https://www.factcheck.org/2019/09/amazon-doesnt-produce-20-of-earths-oxygen/

**Mapper saw** (first 400 chars):
> Q: Does the Amazon produce 20% of the world’s oxygen? A: No. Scientists estimate the percentage is closer to 6 to 9%, and the Amazon ultimately consumes nearly all of that oxygen itself. FULL QUESTION Does the Amazon Rainforest truly produce 20% of the Earth’s oxygen? Where does the remaining 80% come from? FULL ANSWER On Aug. 20, Brazil’s space agency sparked a media frenzy when it released satel

**Beyond window** (+1598 chars):
> lite data showing an alarming number of wildfires in the Amazon rainforest over the past year — nearly 40,000, or a 77% rise compared with the same time period in 2018. Most of the fires have started since June. NASA also has confirmed the surge, declaring 2019 the worst year for wildfires in the region since 2010. Scientists attribute the uptick in fires to increased deforestation, at least some of which, critics say, has been encouraged by Brazil’s president, Jair Bolsonaro. As news outlets ac...

**Mapper reasoning**: Discusses the percentage of oxygen produced by the Amazon rainforest in relation to the world's oxygen, implying global oxygen production can be quantified.

| Field | Value |
|-------|-------|
| Mapper relationship | `context` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `___` (true/false) |
| Notes | |

### ev-7744e79261da -> `context`

**Take a breath: the Amazon does not produce 20% of the world's ...** (AP News, reporting/analysis)
URL: https://apnews.com/article/archive-fact-checking-7106380249

**Mapper saw** (first 400 chars):
> Take a breath: the Amazon does not produce 20% of the world’s oxygen CLAIM: The Amazon rainforest _ “the lungs of the Earth” _ produces 20% of the planet’s oxygen. AP’S ASSESSMENT: False. Scientists say while the Amazon is important to the world’s ecosystem, it does not produce 20% of the world’s oxygen. In fact, the region absorbs about the same amount of oxygen it produces. THE FACTS: The 20% fi

**Beyond window** (+1597 chars):
> gure circulated widely this month as concerns grew around fires burning in the Amazon. It was passed on social media platforms, cited by politicians and quoted by the media, including The Associated Press. The reality, according to experts, is that the Amazon produces and consumes oxygen in nearly perfect balance. That’s because while it produces oxygen through photosynthesis, it also absorbs it to grow, as do animals and microbes. “Even if all plants in the Amazon stopped doing photosynthesis, ...

**Mapper reasoning**: Mentions the world's oxygen production in the context of the Amazon's contribution, implying it can be quantified.

| Field | Value |
|-------|-------|
| Mapper relationship | `context` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `___` (true/false) |
| Notes | |

### ev-rec-e1_0_e82d0bd2 -> `context`

**Amazon Lungs of the Earth: 7 Rainforest Benefits** (farmonaut.com, unclassified/unclassified)
URL: https://farmonaut.com/south-america/amazon-lungs-of-the-earth-7-rainforest-benefits

**Mapper saw** (first 400 chars):
> Through photosynthesis, Amazonian plants absorb CO2 and release oxygen, with the region producing over 20% of the world's atmospheric oxygen. This ongoing cycle ...

**Mapper reasoning**: Mentions the Amazon producing over 20% of the world's atmospheric oxygen, implying a quantifiable total world oxygen production, but does not state the figure.

| Field | Value |
|-------|-------|
| Mapper relationship | `context` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-e1_1_e5366e7b -> `context`

**The Amazon rainforest is dying from the bottom up—tree roots are ...** (facebook.com, unclassified/unclassified)
URL: https://www.facebook.com/groups/physicsisfun109/posts/950888284256683/

**Mapper saw** (first 400 chars):
> The Amazon Rainforest provides 20 percent of the world's oxygen, is home to the greatest biodiversity of species on Earth, and is the world's biggest carbon ...

**Mapper reasoning**: States the Amazon provides 20 percent of the world's oxygen, implying a quantifiable total world oxygen production, but does not state the figure.

| Field | Value |
|-------|-------|
| Mapper relationship | `context` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-e1_2_f5ac46cc -> `context`

**NASA Satellite Measures Saharan Dust Transport to Amazon** (linkedin.com, unclassified/unclassified)
URL: https://www.linkedin.com/posts/william-r-g-3182ba37_nasa-satellite-reveals-how-much-saharan-dust-activity-7383003642485833728-Ve3A

**Mapper saw** (first 400 chars):
> And when the Amazon is alive, it produces oxygen. 20% of the world's oxygen comes from the Amazon, and that oxygen keeps us alive. So yes, our breath is ...

**Mapper reasoning**: States 20% of the world's oxygen comes from the Amazon, implying a quantifiable total world oxygen production, but does not state the figure.

| Field | Value |
|-------|-------|
| Mapper relationship | `context` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-e1_3_563f4056 -> `context`

**Charted: Tropical Forest Loss in 2024** (visualcapitalist.com, unclassified/unclassified)
URL: https://www.visualcapitalist.com/charted-tropical-forest-loss-in-2024/

**Mapper saw** (first 400 chars):
> The Amazon forest alone produces 20% of the world's oxygen, earning it the nickname “the lungs of the planet.” It is also home to over 10% of all known ...

**Mapper reasoning**: Asserts the Amazon produces 20% of the world's oxygen, implying a quantifiable total world oxygen production, but does not state the figure.

| Field | Value |
|-------|-------|
| Mapper relationship | `context` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-e2_1_4ab63237 -> `context`

**World Bank Group's post - Facebook** (facebook.com, unclassified/unclassified)
URL: https://www.facebook.com/worldbank/posts/-the-%F0%9D%90%80%F0%9D%90%A6%F0%9D%90%9A%F0%9D%90%B3%F0%9D%90%A8%F0%9D%90%A7%F0%9D%90%A2%F0%9D%90%9A-spans-67-million-square-kilometers-and-holds-half-of-the-planets-r/1283999727101001/

**Mapper saw** (first 400 chars):
> While it's commonly said that the Amazon produces 20% of the world's oxygen ... For context the Amazon Rainforest would cover roughly 60% of the total United ...

**Mapper reasoning**: Acknowledges the common statement that the Amazon produces 20% of the world's oxygen, implying a quantifiable total world oxygen production, but does not state the figure.

| Field | Value |
|-------|-------|
| Mapper relationship | `context` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### State judgment: `unresolved`

Ref tally: 0 supports, 0 challenges, 7 context

| Field | Value |
|-------|-------|
| Mapper state | `unresolved` |
| Correct? | `___` (true/false) |
| Expected state | `___` (supported/disputed/unresolved) |
| Failure mode | `___` (D/—) |
| Notes | |

---

## e3 — mapper state: `disputed`
*Uncertainty*: The evidence suggests the Amazon produces between 6-9% of the Earth's oxygen, not 20%.

### ev-fbecdcc2008a -> `challenges`

**Amazon Doesn’t Produce 20% of Earth’s Oxygen** (FactCheck.org, reporting/analysis)
URL: https://www.factcheck.org/2019/09/amazon-doesnt-produce-20-of-earths-oxygen/

**Mapper saw** (first 400 chars):
> Q: Does the Amazon produce 20% of the world’s oxygen? A: No. Scientists estimate the percentage is closer to 6 to 9%, and the Amazon ultimately consumes nearly all of that oxygen itself. FULL QUESTION Does the Amazon Rainforest truly produce 20% of the Earth’s oxygen? Where does the remaining 80% come from? FULL ANSWER On Aug. 20, Brazil’s space agency sparked a media frenzy when it released satel

**Beyond window** (+1598 chars):
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

### ev-7744e79261da -> `challenges`

**Take a breath: the Amazon does not produce 20% of the world's ...** (AP News, reporting/analysis)
URL: https://apnews.com/article/archive-fact-checking-7106380249

**Mapper saw** (first 400 chars):
> Take a breath: the Amazon does not produce 20% of the world’s oxygen CLAIM: The Amazon rainforest _ “the lungs of the Earth” _ produces 20% of the planet’s oxygen. AP’S ASSESSMENT: False. Scientists say while the Amazon is important to the world’s ecosystem, it does not produce 20% of the world’s oxygen. In fact, the region absorbs about the same amount of oxygen it produces. THE FACTS: The 20% fi

**Beyond window** (+1597 chars):
> gure circulated widely this month as concerns grew around fires burning in the Amazon. It was passed on social media platforms, cited by politicians and quoted by the media, including The Associated Press. The reality, according to experts, is that the Amazon produces and consumes oxygen in nearly perfect balance. That’s because while it produces oxygen through photosynthesis, it also absorbs it to grow, as do animals and microbes. “Even if all plants in the Amazon stopped doing photosynthesis, ...

**Mapper reasoning**: Explicitly states the claim is false and that the Amazon does not produce 20% of the world's oxygen.

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

- **ev-e68c558e5bc9**: Amazon fires are destructive, but they aren't depleting Earth's ... (The Conversation)
  > Fires in the Amazon rainforest have captured attention worldwide in August. Brazilian President Jair Bolsonaro, who took office in 2019, pledged in hi

- **ev-cf0147c2ba6d**: Amazon rainforest (Wikipedia)
  > The Amazon rainforest, also called the Amazon jungle or Amazonia, is a moist broadleaf tropical rainforest in the Amazon biome that covers most of the

- **ev-87cf7cd86007**: Deforestation of the Amazon rainforest (Wikipedia)
  > The Amazon rainforest, spanning an area of 3,000,000 km2, is the world's largest rainforest. It encompasses the largest and most biodiverse tropical r

- **ev-dccbda7630c0**: Deforestation in Brazil (Wikipedia)
  > Brazil once had the highest deforestation rate in the world, and recent data still shows high rates of deforestation. Between 2001 and 2023, Brazil lo

- **ev-14fa302bde05**: Amazon River (Wikipedia)
  > The Amazon River in South America is the largest river by discharge volume of water in the world, and the longest or second-longest river system in th

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
