# case-014 — Review Sheet

**Claim**: The Amazon river is the longest river globally.
**Type**: empirical | **Model**: gemini-2.5-flash-lite | **Prompt hash**: `429fbbcc6018`

## Elements

- **e1**: The length of the Amazon river can be measured.
- **e2**: The lengths of all other rivers in the world can be measured.
- **e3**: The Amazon river's measured length is greater than the measured length of any other river.

---

## e1 — mapper state: `supported`

### ev-255834e088ff -> `context`

**Amazon River | Facts, History, Location, Length, Animals, & Map** (britannica.com, commentary/analysis)
URL: https://www.britannica.com/place/Amazon-River

**Mapper saw** (first 400 chars):
> Amazon River Where is the Amazon River located. How long is the Amazon River. Why is the Amazon River famous. What animals live in the Amazon River

**Mapper reasoning**: Poses the question 'How long is the Amazon River?', implying its length can be measured.

| Field | Value |
|-------|-------|
| Mapper relationship | `context` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-1e55d586ea33 -> `supports`

**Geography Facts About the Amazon River** (geographyrealm.com, commentary/analysis)
URL: https://www.geographyrealm.com/geography-facts-about-the-amazon-river/

**Mapper saw** (first 400 chars):
> At 3,976 miles (6,400 km) in length, it only narrowly loses the title for the world's longest river to the Nile River in Egypt, which is 4,132 miles (6,650 km) ...

**Mapper reasoning**: Provides a specific length for the Amazon River: 3,976 miles (6,400 km).

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-976a6a4a77aa -> `context`

**Where Does the Amazon River Begin? - National Geographic** (education.nationalgeographic.org, commentary/analysis)
URL: https://education.nationalgeographic.org/resource/where-does-amazon-river-begin/

**Mapper saw** (first 400 chars):
> " When water flows through the Mantaro, the river "probably has a greater flow distance than any other Amazon tributary," Johnston says. But when the Mantaro is dry, "the Apurímac is once again the place where water flows the greatest distance into the Amazon. " It may be more straightforward to trace the source of other rivers, Johnston notes, but "the Amazon, by far the largest river in the worl

**Beyond window** (+184 chars):
> d, is not so simple. " Scientists need to look at all three of its proposed source tributaries—the Marañón, the Apurímac, and the Mantaro—he says, to truly understand the mighty Amazon

**Mapper reasoning**: Discusses tracing the source of the Amazon River, implying its length can be measured.

| Field | Value |
|-------|-------|
| Mapper relationship | `context` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `___` (true/false) |
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

## e2 — mapper state: `unresolved`
*Uncertainty*: While evidence suggests other rivers' lengths can be measured, it does not provide a comprehensive list or confirmation that all other rivers' lengths have been measured and compared.

### ev-16e09dd31de8 -> `context`

**World's longest rivers | Description & Facts | Britannica** (britannica.com, commentary/analysis)
URL: https://www.britannica.com/science/worlds-longest-rivers-2225894

**Mapper saw** (first 400 chars):
> Accurate comparable river-length measurements, however, are often difficult to obtain, because stream definitions and measurement standards vary between countries. It is possible that the main channels of well over 100 of the greatest rivers may exceed 1,600 km (about 1,000 miles) in length. Measuring from the headwaters of the most distant source, the five longest rivers in the world are the Nile

**Beyond window** (+379 chars):
>  (in eastern and northeastern Africa), the Amazon–Ucayali–Apurímac (in South America), the Yangtze (in China), the Mississippi–Missouri–Red Rock (in the United States), and the Yenisey–Baikal–Selenga (in northern Asia). |rank |name |length* |(km) |(miles) |*Figures based on official sources. In countries where the metric system is used, conversions are from kilometres to miles

**Mapper reasoning**: Mentions that comparable river-length measurements can be difficult due to varying standards, but implies that measurements are possible for other rivers.

| Field | Value |
|-------|-------|
| Mapper relationship | `context` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `___` (true/false) |
| Notes | |

### ev-19eba9905a26 -> `context`

**World Rivers: A Comprehensive Overview** (mindmapai.app, commentary/analysis)
URL: https://mindmapai.app/mind-mapping/world-rivers-a-comprehensive-overview

**Mapper saw** (first 400 chars):
> Key Takeaways Indian subcontinent rivers include west-flowing and other major systems. African rivers like Limpopo and Congo cross significant global lines. Amazon is the world's second-longest river by length and largest by discharge. Nile is the longest river globally, while Yangtze is the third longest. Rivers are ranked by basin size and water discharge, with Amazon leading

**Mapper reasoning**: Ranks rivers by length, implying that the lengths of other rivers can be measured.

| Field | Value |
|-------|-------|
| Mapper relationship | `context` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-43a5bd4672a9 -> `context`

**Source apportionment and risk assessment of perfluorinated compounds in the world's third-longest river** (CrossRef, commentary/academic)
URL: https://doi.org/10.5194/egusphere-egu24-12904

**Mapper saw** (first 400 chars):
> <jats:p>This study investigated the pollution of per- and polyfluoroalkyl substances (PFASs)&amp;#160; in sediments from the main stream of the Yangtze River, the world's third-longest river. Totally, 13 of 15 PFASs were detected in the sediments and the total concentrations ranged from 0.058 ng/g t

**Mapper reasoning**: Refers to the 'world's third-longest river', implying lengths of other rivers are measured.

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

## e3 — mapper state: `disputed`

### ev-1e55d586ea33 -> `challenges`

**Geography Facts About the Amazon River** (geographyrealm.com, commentary/analysis)
URL: https://www.geographyrealm.com/geography-facts-about-the-amazon-river/

**Mapper saw** (first 400 chars):
> At 3,976 miles (6,400 km) in length, it only narrowly loses the title for the world's longest river to the Nile River in Egypt, which is 4,132 miles (6,650 km) ...

**Mapper reasoning**: States the Amazon River 'only narrowly loses the title for the world's longest river to the Nile River'.

| Field | Value |
|-------|-------|
| Mapper relationship | `challenges` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-19eba9905a26 -> `challenges`

**World Rivers: A Comprehensive Overview** (mindmapai.app, commentary/analysis)
URL: https://mindmapai.app/mind-mapping/world-rivers-a-comprehensive-overview

**Mapper saw** (first 400 chars):
> Key Takeaways Indian subcontinent rivers include west-flowing and other major systems. African rivers like Limpopo and Congo cross significant global lines. Amazon is the world's second-longest river by length and largest by discharge. Nile is the longest river globally, while Yangtze is the third longest. Rivers are ranked by basin size and water discharge, with Amazon leading

**Mapper reasoning**: States that 'Nile is the longest river globally, while Yangtze is the third longest' and the Amazon is the second-longest.

| Field | Value |
|-------|-------|
| Mapper relationship | `challenges` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-3eda447011eb -> `challenges`

**Which is the Longest River in the World? - Superprof** (superprof.co.in, commentary/analysis)
URL: https://www.superprof.co.in/blog/10-longest-rivers-in-the-world/

**Mapper saw** (first 400 chars):
> Top 10 Longest and Largest Rivers in the World · 1. The Nile River - 6,695 km · 2. The Amazon River - 6,400 km · 3. The Yangtze River - 6,300 km · 4. Mississippi ...

**Mapper reasoning**: Lists the Nile River as the longest (6,695 km) and the Amazon River as the second longest (6,400 km).

| Field | Value |
|-------|-------|
| Mapper relationship | `challenges` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-16e09dd31de8 -> `challenges`

**World's longest rivers | Description & Facts | Britannica** (britannica.com, commentary/analysis)
URL: https://www.britannica.com/science/worlds-longest-rivers-2225894

**Mapper saw** (first 400 chars):
> Accurate comparable river-length measurements, however, are often difficult to obtain, because stream definitions and measurement standards vary between countries. It is possible that the main channels of well over 100 of the greatest rivers may exceed 1,600 km (about 1,000 miles) in length. Measuring from the headwaters of the most distant source, the five longest rivers in the world are the Nile

**Beyond window** (+379 chars):
>  (in eastern and northeastern Africa), the Amazon–Ucayali–Apurímac (in South America), the Yangtze (in China), the Mississippi–Missouri–Red Rock (in the United States), and the Yenisey–Baikal–Selenga (in northern Asia). |rank |name |length* |(km) |(miles) |*Figures based on official sources. In countries where the metric system is used, conversions are from kilometres to miles

**Mapper reasoning**: Lists the Nile as one of the five longest rivers in the world, without explicitly stating the Amazon is longer.

| Field | Value |
|-------|-------|
| Mapper relationship | `challenges` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `___` (true/false) |
| Notes | |

### State judgment: `disputed`

Ref tally: 0 supports, 4 challenges, 0 context

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

- **ev-f1a1c17eddbd**: Top 30 Rivers in the World by discharge rate : r/charts - Reddit (reddit.com)
  > The flow of The Amazon is so great it extends fresh water about 80 kilometers into the Atlantic Ocean.

- **ev-4e6f52335b29**: The Longest River in the World: Nile vs Amazon - YouTube (youtube.com)
  > Before you continue to YouTube We use cookies and data to - Deliver and maintain Google services - Track outages and protect against spam, fraud and a

- **ev-ea841c166495**: Top 10 Longest Rivers in the World - YouTube (youtube.com)
  > About Press Copyright Contact us Creator Advertise Developers Terms

- **ev-01f7e0388076**: Amazon River may be altered forever by climate change (CrossRef)
  > Academic research: Amazon River may be altered forever by climate change

- **ev-52e7a0685c62**: Modulation of Amazon River Plume: numerical studies (CrossRef)
  > <jats:p>The Amazon River Plume (ARP) is a dynamic feature of the Amazon Shelf (AS), shaped by a combination of natural forces: density-driven currents

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
