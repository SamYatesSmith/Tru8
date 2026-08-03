# case-016 — Review Sheet

**Claim**: The number of Amazon employees globally exceeded 1.5 million in the year 2023.
**Type**: empirical | **Model**: gemini-2.5-flash-lite | **Prompt hash**: `dc758f537aec`

## Elements

- **e1**: Amazon's total employee count is determined by summing all individuals employed by the company across all its global operations.
- **e2**: The year in question for the employee count is 2023.
- **e3**: The total number of Amazon employees worldwide was greater than 1,500,000.

---

## e1 — mapper state: `unresolved`

*No evidence mapped to this element.*

### State judgment: `unresolved`

| Field | Value |
|-------|-------|
| Mapper state | `unresolved` |
| Correct? | `___` (true/false) |
| Expected state | `___` |
| Failure mode | `___` (A/B/C/D/—) |
| Notes | |

---

## e2 — mapper state: `unresolved`
*Uncertainty*: The provided evidence mentions 2023 in relation to corporate roles and workforce figures, but does not explicitly state that 2023 is the year for the overall employee count being discussed.

### ev-5f868db26046 -> `context`

**How many Amazon distribution workers are in each state?** (ontheseams.substack.com, commentary/data)
URL: https://ontheseams.substack.com/p/how-many-amazon-distribution-workers

**Mapper saw** (first 400 chars):
> I determined the 2024 average number of employees per facility according to same methodology described for the 2023 count here. Here are the 2024 average number of employee numbers: And here finally are the results: you can see the full spreadsheet here. The analysis produced a total of 913,546 workers in Amazon’s distribution network, which strikes me as in the ballpark. Amazon claims to have 1. 

**Beyond window** (+55 chars):
> 556 million workers on its 10-K, and somewhere around 1

**Mapper reasoning**: —

| Field | Value |
|-------|-------|
| Mapper relationship | `context` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `___` (true/false) |
| Notes | |

### ev-7b177879b47e -> `context`

**Amazon confirms 16000 more corporate job cuts, bringing total to ...** (geekwire.com, reporting/news_reporting)
URL: https://www.geekwire.com/2026/amazon-confirms-16000-more-job-cuts-bringing-total-layoffs-to-30000-since-october/

**Mapper saw** (first 400 chars):
> The company's corporate roles numbered around 350,000 people in early 2023, the last time Amazon provided a public figure. Its overall workforce stands at 1.57 ...

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

Ref tally: 0 supports, 0 challenges, 2 context

| Field | Value |
|-------|-------|
| Mapper state | `unresolved` |
| Correct? | `___` (true/false) |
| Expected state | `___` (supported/disputed/unresolved) |
| Failure mode | `___` (D/—) |
| Notes | |

---

## e3 — mapper state: `supported`

### ev-5b20eadb9a63 -> `supports`

**Number of Amazon Employees (2025) - Exploding Topics** (explodingtopics.com, commentary/data)
URL: https://explodingtopics.com/blog/amazon-employees

**Mapper saw** (first 400 chars):
> And between 2017 and 2022, this figure increased to 975,000. In fact, the number of Amazon employees has only dropped twice since 2007. In 2021, Amazon employed around 1,608,000 people – 67,000 fewer than 2022’s end-of-year total (1,541,000). Since 2007 (17,000 employees), the number of Amazon employees has increased by over 90x. Here’s a breakdown of the number of employees that work at Amazon ov

**Beyond window** (+151 chars):
> er time: | Year | Amazon Employees | Change Over Previous Year | Change Over Previous Year (%) | 2007 | 17,000 | - | - | 2008 | 20,700 | ↑ 2,300 | ↑ 21

**Mapper reasoning**: —

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `___` (true/false) |
| Notes | |

### ev-0f989d21f37d -> `supports`

**[BREAKING] Amazon to layoff 30,000 corporate employees in one of ...** (reddit.com, commentary/news_reporting)
URL: https://www.reddit.com/r/cscareerquestions/comments/1ohnh7q/breaking_amazon_to_layoff_30000_corporate/

**Mapper saw** (first 400 chars):
> The figure represents a small percentage of Amazon's 1.55 million total employees, but nearly 10% of the company's roughly 350,000 corporate employees. This ...

**Mapper reasoning**: —

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-5f4ef17adc63 -> `supports`

**Amazon Layoffs: One Chart Shows How Much the Tech Giant Has ...** (businessinsider.com, reporting/news_reporting)
URL: https://www.businessinsider.com/layoffs-one-chart-amazon-hiring-pandemic-great-resignation-2025-10

**Mapper saw** (first 400 chars):
> The Big Tech company expanded to over a million full-time and part-time employees in 2020, climbing to 1. 6 million a year later when there was a lot of turnover in the overall US workforce as the economy reopened after the pandemic-induced recession. Amazon's workforce has roughly tripled between 2017 and 2024. Beth Galetti, senior vice president of people experience and technology at Amazon, sai

**Beyond window** (+354 chars):
> d in a message to workers on Tuesday that the new cuts "are a continuation of this work to get even stronger by further reducing bureaucracy, removing layers, and shifting resources to ensure we're investing in our biggest bets and what matters most to our customers' current and future needs. " Amazon is just one large company that's laying off workers

**Mapper reasoning**: —

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `___` (true/false) |
| Notes | |

### ev-7b177879b47e -> `supports`

**Amazon confirms 16000 more corporate job cuts, bringing total to ...** (geekwire.com, reporting/news_reporting)
URL: https://www.geekwire.com/2026/amazon-confirms-16000-more-job-cuts-bringing-total-layoffs-to-30000-since-october/

**Mapper saw** (first 400 chars):
> The company's corporate roles numbered around 350,000 people in early 2023, the last time Amazon provided a public figure. Its overall workforce stands at 1.57 ...

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

- **ev-03cb65d3fa4e**: How many people work for Amazon? (2025 data) (redstagfulfillment.com)
  > How many people work for Amazon. (2025 data) Amazon employs approximately 1. 56 million full- and part-time workers worldwide as of early 2025, accord

- **ev-42a6ab39a0c4**: Amazon employees 2025| Statista (statista.com)
  > srsltid=AfmBOoqRLQTqw2NElfpoIbiNj9NesN_El_Xb3pMHrXarA11WGq5CfBMx Amazon, U. Securities and Exchange Commission. Employees of Amazon from 2007 to 2025.

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
