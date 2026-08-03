# case-010 — Review Sheet

**Claim**: Ethereum's shift to proof-of-stake resulted in a 99% reduction in its energy consumption.
**Type**: causal_interpretive | **Model**: gemini-2.5-flash-lite | **Prompt hash**: `17bef1b58434`

## Elements

- **e1**: The energy consumption of the Ethereum network before the proof-of-stake transition can be measured.
- **e2**: The energy consumption of the Ethereum network after the proof-of-stake transition can be measured.
- **e3**: The transition to proof-of-stake was the primary cause of the change in energy consumption.
- **e4**: The measured reduction in energy consumption is approximately 99%.

---

## e1 — mapper state: `unresolved`
*Uncertainty*: While evidence indicates Ethereum used proof-of-work previously, it does not provide a specific measurement of its energy consumption before the transition.

### ev-rec-5_3_c3474498 -> `context`

**Danny Ryan on Ethereum's Biggest Upgrade, the SEC, & the $120 ...** (etherworld.co, commentary/analysis)
URL: https://etherworld.co/danny-ryan-on-ethereums-biggest-upgrade-the-sec-the-120-trillion-question/

**Mapper saw** (first 400 chars):
> Ethereum was transitioning from Proof of Work to Proof of Stake without stopping the network. Billions of dollars were secured by that code. The Merge ...

**Mapper reasoning**: Mentions the transition from Proof of Work to Proof of Stake but does not quantify pre-transition energy consumption.

| Field | Value |
|-------|-------|
| Mapper relationship | `context` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### State judgment: `unresolved`

Ref tally: 0 supports, 0 challenges, 1 context

| Field | Value |
|-------|-------|
| Mapper state | `unresolved` |
| Correct? | `___` (true/false) |
| Expected state | `___` (supported/disputed/unresolved) |
| Failure mode | `___` (D/—) |
| Notes | |

---

## e2 — mapper state: `supported`

### ev-rec-5_0_4f641eaa -> `supports`

**What is the EIP-3675 update? | Crypto Academy - Finst** (finst.com, commentary/analysis)
URL: https://finst.com/en/learn/articles/what-is-eip-3675

**Mapper saw** (first 400 chars):
> By transitioning to Proof of Stake, Ethereum's energy consumption dropped by more than 99%. This made Ethereum significantly more environmentally friendly ...

**Mapper reasoning**: States that by transitioning to Proof of Stake, Ethereum's energy consumption dropped, implying a measurable consumption after the transition.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### State judgment: `supported`

Ref tally: 1 supports, 0 challenges, 0 context

| Field | Value |
|-------|-------|
| Mapper state | `supported` |
| Correct? | `___` (true/false) |
| Expected state | `___` (supported/disputed/unresolved) |
| Failure mode | `___` (D/—) |
| Notes | |

---

## e3 — mapper state: `supported`

### ev-rec-5_0_4f641eaa -> `supports`

**What is the EIP-3675 update? | Crypto Academy - Finst** (finst.com, commentary/analysis)
URL: https://finst.com/en/learn/articles/what-is-eip-3675

**Mapper saw** (first 400 chars):
> By transitioning to Proof of Stake, Ethereum's energy consumption dropped by more than 99%. This made Ethereum significantly more environmentally friendly ...

**Mapper reasoning**: Explicitly states 'By transitioning to Proof of Stake, Ethereum's energy consumption dropped by more than 99%', directly linking the transition to the reduction.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-5_1_aef46242 -> `supports`

**Ethereum's Shift to Proof of Stake Cuts Energy Use by 99% - LinkedIn** (linkedin.com, commentary/analysis)
URL: https://www.linkedin.com/posts/legacyquant_ethereum-blockchain-sustainability-activity-7425128411884486656-18JI

**Mapper saw** (first 400 chars):
> Ethereum's Shift to Proof of Stake Cuts Energy Use by 99% | Legacy Quant Trading AI posted on the topic | LinkedIn.

**Mapper reasoning**: The title 'Ethereum's Shift to Proof of Stake Cuts Energy Use by 99%' directly attributes the reduction to the shift.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-5_2_f08ef83e -> `supports`

**10 Defining Moments in Ethereum's First 10 Years - Coin Metrics** (coinmetrics.io, commentary/analysis)
URL: https://coinmetrics.io/news/10-years-of-ethereum/

**Mapper saw** (first 400 chars):
> Energy usage dropped by more than 99%, and Ethereum became the most prominent proof-of-stake blockchain overnight.

**Mapper reasoning**: States 'Energy usage dropped by more than 99%, and Ethereum became the most prominent proof-of-stake blockchain overnight', linking the drop to becoming PoS.

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

## e4 — mapper state: `supported`

### ev-rec-5_0_4f641eaa -> `supports`

**What is the EIP-3675 update? | Crypto Academy - Finst** (finst.com, commentary/analysis)
URL: https://finst.com/en/learn/articles/what-is-eip-3675

**Mapper saw** (first 400 chars):
> By transitioning to Proof of Stake, Ethereum's energy consumption dropped by more than 99%. This made Ethereum significantly more environmentally friendly ...

**Mapper reasoning**: States 'Ethereum's energy consumption dropped by more than 99%'.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-5_1_aef46242 -> `supports`

**Ethereum's Shift to Proof of Stake Cuts Energy Use by 99% - LinkedIn** (linkedin.com, commentary/analysis)
URL: https://www.linkedin.com/posts/legacyquant_ethereum-blockchain-sustainability-activity-7425128411884486656-18JI

**Mapper saw** (first 400 chars):
> Ethereum's Shift to Proof of Stake Cuts Energy Use by 99% | Legacy Quant Trading AI posted on the topic | LinkedIn.

**Mapper reasoning**: Title states 'Ethereum's Shift to Proof of Stake Cuts Energy Use by 99%'.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-5_2_f08ef83e -> `supports`

**10 Defining Moments in Ethereum's First 10 Years - Coin Metrics** (coinmetrics.io, commentary/analysis)
URL: https://coinmetrics.io/news/10-years-of-ethereum/

**Mapper saw** (first 400 chars):
> Energy usage dropped by more than 99%, and Ethereum became the most prominent proof-of-stake blockchain overnight.

**Mapper reasoning**: States 'Energy usage dropped by more than 99%'.

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

## Missing refs

Evidence the mapper should have mapped but didn't:

- **ev-rec-5_5_2e9b21eb**: Canary MOG ETF S-1 - SEC.gov (sec.gov)
  > In proof-of-stake, validators stake ETH to compete to be selected to propose and attest to blocks of transactions and are rewarded in proportion to th

- **ev-rec-5_6_7a4c360f**: tm2519799-1_s1 - none - 14.7656219s - SEC.gov (sec.gov)
  > The move to proof-of-stake may subject Ethereum and ether to new and unexpected vulnerabilities not applicable to proof-of-work consensus models. Hist

- **ev-rec-5_8_f797e828**: S-1 - SEC.gov (sec.gov)
  > In June 2016, an anonymous hacker exploited a smart contract running on the Ethereum Network to syphon approximately $60 million of Ether held by The 

- **ev-rec-5_4_95ca6a28**: iset20251205_s1.htm - SEC.gov (sec.gov)
  > Under the Trust's staking program, the Sponsor instructs the Ether Custodian to stake the Trust's ether. The Ether Custodian then delegates a specifie

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
