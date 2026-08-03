# case-015 — Review Sheet

**Claim**: The Great Wall of China is visible from space with the naked eye.
**Type**: empirical | **Model**: gemini-2.5-flash-lite | **Prompt hash**: `2ddb43f30238`

## Elements

- **e1**: The Great Wall of China is a physical structure that can be observed.
- **e2**: There exists a vantage point in space from which observations can be made.
- **e3**: The human eye, without optical aid, is capable of perceiving the Great Wall of China from that vantage point.

---

## e1 — mapper state: `supported`

### ev-343cece8454e -> `supports`

**Great Wall of China** (Wikipedia, primary/data)
URL: https://en.wikipedia.org/wiki/Great_Wall_of_China

**Mapper saw** (first 400 chars):
> The Great Wall of China is a series of fortifications in China. They were built across the historical northern borders of ancient Chinese states and Imperial China as protection against various nomadic groups from the Eurasian Steppe. The first walls date to the 7th century BC; these were joined together in the Qin dynasty. Successive dynasties expanded the wall system; the best-known sections wer

**Beyond window** (+40 chars):
> e built by the Ming dynasty (1368–1644).

**Mapper reasoning**: Describes the Great Wall of China as a series of fortifications built across historical northern borders, confirming it is a physical structure.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `___` (true/false) |
| Notes | |

### ev-100341d813bd -> `supports`

**Curiosity: Is the Great Wall of China visible from space with the ...** (timesofmalta.com, commentary/analysis)
URL: https://timesofmalta.com/article/curiosity-is-great-wall-china-visible-space-naked-eye.1106177

**Mapper saw** (first 400 chars):
> Curiosity: Is the Great Wall of China visible from space with the naked eye It's the longest man-made structure in the world Measuring an astounding total of 21,196 kilometres, the Great Wall of China is indeed the longest man-made structure in the world. However, even though it boasts such an impressive length, it is only approximately six metres at its widest – at the wall base itself. This, cou

**Beyond window** (+261 chars):
> pled with the fact that the Great Wall is made of materials that indeed look very similar to the neighbouring terrain, means that the Great Wall is actually not visible from space, even from low Earth orbit at an altitude of some 160km above the Earth’s surface

**Mapper reasoning**: States the Great Wall of China is the longest man-made structure in the world, measuring 21,196 kilometers, confirming its existence as a physical structure.

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

## e2 — mapper state: `supported`

### ev-4261bdd01d2b -> `supports`

**Great Wall of China is visible from space: Fact or myth?** (timesofindia.indiatimes.com, commentary/analysis)
URL: https://timesofindia.indiatimes.com/life-style/travel/news/great-wall-of-china-is-visible-from-space-fact-or-myth/articleshow/128671144.cms

**Mapper saw** (first 400 chars):
> NASA astronauts have echoed similar observations. According to NASA , while certain human-made structures can be seen from low Earth orbit under ideal conditions, the Great Wall is not easily distinguishable without visual aid. NASA's comment on Great Wall of China being seen from space Why it’s so hard to see At first glance, this seems surprising. The Great Wall stretches more than 21,000 kilome

**Beyond window** (+122 chars):
> ters in total length (including natural barriers and trenches). But here’s the catch: length isn’t the issue, the width is

**Mapper reasoning**: Mentions observations from low Earth orbit by NASA astronauts, indicating a vantage point in space from which observations can be made.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `___` (true/false) |
| Notes | |

### ev-57b48fe392ab -> `supports`

**Forget the Great Wall: The Human Landmark Astronauts Actually ...** (billysbeds.com.au, commentary/analysis)
URL: https://billysbeds.com.au/forget-the-great-wall-the-human-landmark-astronauts-actually-see-from-space/?srsltid=AfmBOoqfyqRPk27qHvmaVkd_h35T0RdHXTnDKHsIrTNHc6gNwBW0TYD_

**Mapper saw** (first 400 chars):
> What Astronauts Really See From low Earth orbit — such as aboard the International Space Station — the most visible human features are typically those that maximize brightness and contrast. Here’s how various landmarks compare: - Cities at night: Clearly visible due to artificial lighting. - Great Wall of China: Rarely visible due to low contrast. - Almería greenhouses: Often visible thanks to ref

**Beyond window** (+96 chars):
> lectivity and scale. - Large open-pit mines: Frequently visible because of exposed rock and size

**Mapper reasoning**: Refers to observations from low Earth orbit, such as aboard the International Space Station, confirming a vantage point in space.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `___` (true/false) |
| Notes | |

### ev-5a1e621ec551 -> `context`

**Forget the Great Wall: the human landmark astronauts actually see ...** (futura-sciences.com, commentary/analysis)
URL: https://www.futura-sciences.com/en/its-not-the-great-wall-heres-the-most-visible-human-made-structure-from-space_24815/

**Mapper saw** (first 400 chars):
> The Great Wall myth: a 300-year-old guess The idea that the Great Wall of China is visible from the Moon didn’t start with the space age; it likely traces back to 18th century writers who were simply guessing. Since the Apollo missions, astronauts have consistently pushed back on this. Apollo crew members, including Neil Armstrong and others, have noted that from the Moon you can make out Earth’s 

**Beyond window** (+99 chars):
> continents and clouds, but essentially no specific human made structure stands out to the naked eye

**Mapper reasoning**: Discusses observations made from the Moon during Apollo missions, providing context for space vantage points.

| Field | Value |
|-------|-------|
| Mapper relationship | `context` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `___` (true/false) |
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

## e3 — mapper state: `disputed`
*Uncertainty*: While some sources claim the Great Wall is visible, multiple astronaut accounts and scientific explanations indicate it is not easily distinguishable without aid and is rarely visible due to low contrast.

### ev-41b6720224f2 -> `challenges`

**Is the Great Wall of China Visible from the Moon?** (Snopes, commentary/analysis)
URL: https://www.snopes.com/fact-check/great-wall-from-moon/

**Mapper saw** (first 400 chars):
> The claim that China's Great Wall is the only man-made object that can be seen from the moon with the naked eye is one of our more tenaciously incorrect "facts," a bit of erroneous speculation which was spawned decades before we had the means to demonstrate it true, and which continues to have currency despite having long since been proved false. Some less specific versions of the Great Wall claim

**Beyond window** (+1600 chars):
>  maintain it is the only man-made object that can be seen from "space," but although the term "space" is rather non-specific, it is not difficult to show the Great Wall claim to be false for any reasonable definition of the term. If we take "space" to mean a low Earth orbit such as the one traveled by the Space Shuttle (roughly 160 to 350 miles above Earth), the Great Wall claim fails twice. First of all, it's not the only object visible from that distance: NASA's Earth from Space photographic a...

**Mapper reasoning**: States that the claim of the Great Wall being seen from the Moon with the naked eye is an 'erroneous speculation' that has been 'proved false'.

| Field | Value |
|-------|-------|
| Mapper relationship | `challenges` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `___` (true/false) |
| Notes | |

### ev-4261bdd01d2b -> `challenges`

**Great Wall of China is visible from space: Fact or myth?** (timesofindia.indiatimes.com, commentary/analysis)
URL: https://timesofindia.indiatimes.com/life-style/travel/news/great-wall-of-china-is-visible-from-space-fact-or-myth/articleshow/128671144.cms

**Mapper saw** (first 400 chars):
> NASA astronauts have echoed similar observations. According to NASA , while certain human-made structures can be seen from low Earth orbit under ideal conditions, the Great Wall is not easily distinguishable without visual aid. NASA's comment on Great Wall of China being seen from space Why it’s so hard to see At first glance, this seems surprising. The Great Wall stretches more than 21,000 kilome

**Beyond window** (+122 chars):
> ters in total length (including natural barriers and trenches). But here’s the catch: length isn’t the issue, the width is

**Mapper reasoning**: Notes that the Great Wall is not easily distinguishable without visual aid, contradicting the idea of naked-eye visibility from space.

| Field | Value |
|-------|-------|
| Mapper relationship | `challenges` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `___` (true/false) |
| Notes | |

### ev-0ffb39bff315 -> `challenges`

**TIL the Great Wall of China is not actually visible from space, its just ...** (reddit.com, commentary/opinion)
URL: https://www.reddit.com/r/todayilearned/comments/1kg3uwe/til_the_great_wall_of_china_is_not_actually/

**Mapper saw** (first 400 chars):
> The Great Wall of China is the only man made structure big enough to be seen from outer space with the naked eye. You can 100% see the Great Wall of China from ...

**Mapper reasoning**: Directly states that the Great Wall of China is not actually visible from space with the naked eye, despite its size.

| Field | Value |
|-------|-------|
| Mapper relationship | `challenges` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-5a1e621ec551 -> `challenges`

**Forget the Great Wall: the human landmark astronauts actually see ...** (futura-sciences.com, commentary/analysis)
URL: https://www.futura-sciences.com/en/its-not-the-great-wall-heres-the-most-visible-human-made-structure-from-space_24815/

**Mapper saw** (first 400 chars):
> The Great Wall myth: a 300-year-old guess The idea that the Great Wall of China is visible from the Moon didn’t start with the space age; it likely traces back to 18th century writers who were simply guessing. Since the Apollo missions, astronauts have consistently pushed back on this. Apollo crew members, including Neil Armstrong and others, have noted that from the Moon you can make out Earth’s 

**Beyond window** (+99 chars):
> continents and clouds, but essentially no specific human made structure stands out to the naked eye

**Mapper reasoning**: Mentions that astronauts have consistently pushed back on the idea that the Great Wall is visible from the Moon, indicating it's not easily seen.

| Field | Value |
|-------|-------|
| Mapper relationship | `challenges` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `___` (true/false) |
| Notes | |

### ev-31f6b0ae6efe -> `challenges`

**Can the Great Wall Be Seen from the Space? - Travel China Guide** (travelchinaguide.com, commentary/analysis)
URL: https://www.travelchinaguide.com/china_great_wall/facts/seen-from-space.htm

**Mapper saw** (first 400 chars):
> Can the Great Wall Be Seen from the Space. It was once widely believed that the Great Wall could be seen from space. However, as humans ventured into space, this myth was completely debunked

**Mapper reasoning**: States that the belief the Great Wall could be seen from space was a myth that was 'completely debunked' as humans ventured into space.

| Field | Value |
|-------|-------|
| Mapper relationship | `challenges` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-dd70f1ce4877 -> `challenges`

**This human landmark truly shines from space, not the Great Wall of ...** (moneycontrol.com, commentary/analysis)
URL: https://www.moneycontrol.com/science/this-human-landmark-truly-shines-from-space-not-the-great-wall-of-china-say-astronauts-article-13821635.html

**Mapper saw** (first 400 chars):
> This human landmark truly shines from space, not the Great Wall of China, say astronauts For centuries, people believed the Great Wall ruled space views, yet astronauts spotted something else entirely. A vast white landscape in Spain quietly rewrote what humanity leaves visible from orbit. February 10, 2026 / 15:24 IST The Great Wall Isn’t What Astronauts See From Orbit, This Shimmering Human Foot

**Beyond window** (+512 chars):
> print Is (Image: Canva) The article explores why the Great Wall of China is rarely visible from space, despite long held myths, and how Spain’s Almería greenhouses became one of Earth’s clearest human made features from orbit. Astronaut accounts reveal that contrast, scale and reflectivity matter more than history. While the plastic covered farmland feeds much of Europe, its visibility highlights environmental costs, showing how modern activity now leaves stronger planetary fingerprints than anc...

**Mapper reasoning**: Asserts that the Great Wall isn't what astronauts see from orbit, implying it's not readily visible.

| Field | Value |
|-------|-------|
| Mapper relationship | `challenges` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `___` (true/false) |
| Notes | |

### ev-57b48fe392ab -> `challenges`

**Forget the Great Wall: The Human Landmark Astronauts Actually ...** (billysbeds.com.au, commentary/analysis)
URL: https://billysbeds.com.au/forget-the-great-wall-the-human-landmark-astronauts-actually-see-from-space/?srsltid=AfmBOoqfyqRPk27qHvmaVkd_h35T0RdHXTnDKHsIrTNHc6gNwBW0TYD_

**Mapper saw** (first 400 chars):
> What Astronauts Really See From low Earth orbit — such as aboard the International Space Station — the most visible human features are typically those that maximize brightness and contrast. Here’s how various landmarks compare: - Cities at night: Clearly visible due to artificial lighting. - Great Wall of China: Rarely visible due to low contrast. - Almería greenhouses: Often visible thanks to ref

**Beyond window** (+96 chars):
> lectivity and scale. - Large open-pit mines: Frequently visible because of exposed rock and size

**Mapper reasoning**: States the Great Wall of China is 'rarely visible' from low Earth orbit due to low contrast, directly challenging naked-eye visibility.

| Field | Value |
|-------|-------|
| Mapper relationship | `challenges` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `___` (true/false) |
| Notes | |

### ev-6cf0c6342ff8 -> `context`

**Artificial structures visible from space** (Wikipedia, primary/data)
URL: https://en.wikipedia.org/wiki/Artificial_structures_visible_from_space

**Mapper saw** (first 400 chars):
> Artificial structures visible from space without magnification include highways, dams, and cities.

**Mapper reasoning**: Lists other artificial structures like highways, dams, and cities as visible from space without magnification, providing context for what is visible.

| Field | Value |
|-------|-------|
| Mapper relationship | `context` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### State judgment: `disputed`

Ref tally: 0 supports, 7 challenges, 1 context

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

- **ev-66a07338993e**: Can you actually see the Great Wall of China from space? - YouTube (youtube.com)
  > Select 'More options' to see additional information, including details about managing your privacy settings

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
