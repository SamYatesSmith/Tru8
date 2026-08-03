# case-008 — Review Sheet

**Claim**: The Amazon river is the longest river globally.
**Type**: empirical | **Model**: gemini-2.5-flash-lite | **Prompt hash**: `d9c0078808a4`

## Elements

- **e1**: The length of the Amazon river can be measured.
- **e2**: The lengths of all other major rivers in the world can be measured.
- **e3**: The Amazon river's measured length is greater than the measured length of any other river.

---

## e1 — mapper state: `supported`

### ev-rec-e1_0_346ed6d7 -> `supports`

**Amazon River | Facts, History, Location, Length, Animals, & Map** (britannica.com, unclassified/unclassified)
URL: https://www.britannica.com/place/Amazon-River

**Mapper saw** (first 400 chars):
> While there is some debate about its length, the river is generally believed to be at least 4,000 miles (6,400 km) long, which makes it the second longest river ...

**Mapper reasoning**: States the Amazon River is generally believed to be at least 4,000 miles long, indicating its length can be measured.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-e1_1_9bc51699 -> `supports`

**Where Does the Amazon River Begin? - National Geographic** (education.nationalgeographic.org, unclassified/unclassified)
URL: https://education.nationalgeographic.org/resource/where-does-amazon-river-begin/

**Mapper saw** (first 400 chars):
> If they're right, their discovery would add 47 to 57 miles (75 to 92 kilometers) to the length of the Amazon, currently measured at about 4,000 miles (6,437 ...

**Mapper reasoning**: Mentions a current measurement of the Amazon River at about 4,000 miles, confirming its length is measured.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-e1_2_015ac81e -> `supports`

**Amazon river facts and geography - Facebook** (facebook.com, unclassified/unclassified)
URL: https://www.facebook.com/groups/8633729870037397/posts/9889991174411254/

**Mapper saw** (first 400 chars):
> THE LONGEST RIVER IN THE WORLD The Amazon River measures 7020 km, originates at the foot of the Mismi mountain in Peru and empties into the Atlantic ...

**Mapper reasoning**: Provides a specific measurement for the Amazon River: 7020 km.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-e1_3_4ab7e69f -> `supports`

**Mapped: The 15 Longest Rivers in the World - Visual Capitalist** (visualcapitalist.com, unclassified/unclassified)
URL: https://www.visualcapitalist.com/mapped-the-15-longest-rivers-in-the-world/

**Mapper saw** (first 400 chars):
> Experts disagree on the length of the Amazon—some measurements put it at 4,345 miles (6,992 km), narrowly edging out the Nile. China's Yangtze is the ...

**Mapper reasoning**: Notes that some measurements put the Amazon's length at 4,345 miles (6,992 km), indicating it is measured.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-e1_4_65bdb51c -> `supports`

**Geography Facts About the Amazon River** (geographyrealm.com, unclassified/unclassified)
URL: https://www.geographyrealm.com/geography-facts-about-the-amazon-river/

**Mapper saw** (first 400 chars):
> The Amazon River located in South America is the world's second longest river. At 3,976 miles (6,400 km) in length, it only narrowly loses the title for the ...

**Mapper reasoning**: States the Amazon River is 3,976 miles (6,400 km) in length, confirming it is measured.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### State judgment: `supported`

Ref tally: 5 supports, 0 challenges, 0 context

| Field | Value |
|-------|-------|
| Mapper state | `supported` |
| Correct? | `___` (true/false) |
| Expected state | `___` (supported/disputed/unresolved) |
| Failure mode | `___` (D/—) |
| Notes | |

---

## e2 — mapper state: `supported`
*Uncertainty*: The evidence primarily focuses on the Amazon and Nile, but implies other major rivers can also be measured.

### ev-rec-e2_1_8e292d25 -> `supports`

**Understanding Rivers - National Geographic Education** (education.nationalgeographic.org, unclassified/unclassified)
URL: https://education.nationalgeographic.org/resource/understanding-rivers/

**Mapper saw** (first 400 chars):
> The Amazon River is about 6,437 kilometers (4,000 miles) long, while the Nile River is about 6,650 kilometers (4,135 miles) long. There is no debate, however, ...

**Mapper reasoning**: Provides measurements for both the Amazon River (6,437 km) and the Nile River (6,650 km), implying these lengths can be measured.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-e3_1_c8bb72da -> `supports`

**The world's longest rivers, ranked by length. The Nile or the Amazon ...** (facebook.com, unclassified/unclassified)
URL: https://www.facebook.com/fromquarktoquasars/posts/the-worlds-longest-rivers-ranked-by-lengththe-nile-or-the-amazon-scientists-stil/1415753193495942/

**Mapper saw** (first 400 chars):
> The #Amazon River is 6,992.06 kilometers long, originating at the foot of Mount Mismi in Peru and flowing into the Atlantic Ocean in Brazil. For centuries, the ...

**Mapper reasoning**: States the Amazon River's length as 6,992.06 kilometers, indicating its length is measured.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-e3_4_2bd08f08 -> `supports`

**Is the Amazon or the Nile the Longest Reiver in the World? Depends ...** (voronoiapp.com, unclassified/unclassified)
URL: https://www.voronoiapp.com/nature/-Is-the-Amazon-or-the-Nile-the-Longest-Reiver-in-the-World-Depends-Who-You-Ask-7113

**Mapper saw** (first 400 chars):
> While there is a consensus on the Nile being the longest, some experts list the Amazon's length at 4,345 miles (6,992 km), making it 300 miles (342 km) longer ...

**Mapper reasoning**: Mentions experts listing the Amazon's length at 4,345 miles (6,992 km) and the Nile's length, implying these can be measured.

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

## e3 — mapper state: `disputed`
*Uncertainty*: There is conflicting information regarding whether the Amazon or the Nile is the longest river.

### ev-rec-e1_0_346ed6d7 -> `challenges`

**Amazon River | Facts, History, Location, Length, Animals, & Map** (britannica.com, unclassified/unclassified)
URL: https://www.britannica.com/place/Amazon-River

**Mapper saw** (first 400 chars):
> While there is some debate about its length, the river is generally believed to be at least 4,000 miles (6,400 km) long, which makes it the second longest river ...

**Mapper reasoning**: States the Amazon is the second longest river, directly contradicting the claim that it is the longest.

| Field | Value |
|-------|-------|
| Mapper relationship | `challenges` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-e1_4_65bdb51c -> `challenges`

**Geography Facts About the Amazon River** (geographyrealm.com, unclassified/unclassified)
URL: https://www.geographyrealm.com/geography-facts-about-the-amazon-river/

**Mapper saw** (first 400 chars):
> The Amazon River located in South America is the world's second longest river. At 3,976 miles (6,400 km) in length, it only narrowly loses the title for the ...

**Mapper reasoning**: Explicitly states the Amazon River is the world's second longest river, challenging the claim.

| Field | Value |
|-------|-------|
| Mapper relationship | `challenges` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-e2_1_8e292d25 -> `challenges`

**Understanding Rivers - National Geographic Education** (education.nationalgeographic.org, unclassified/unclassified)
URL: https://education.nationalgeographic.org/resource/understanding-rivers/

**Mapper saw** (first 400 chars):
> The Amazon River is about 6,437 kilometers (4,000 miles) long, while the Nile River is about 6,650 kilometers (4,135 miles) long. There is no debate, however, ...

**Mapper reasoning**: States the Nile River is longer (6,650 km) than the Amazon River (6,437 km), challenging the claim.

| Field | Value |
|-------|-------|
| Mapper relationship | `challenges` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-e1_3_4ab7e69f -> `context`

**Mapped: The 15 Longest Rivers in the World - Visual Capitalist** (visualcapitalist.com, unclassified/unclassified)
URL: https://www.visualcapitalist.com/mapped-the-15-longest-rivers-in-the-world/

**Mapper saw** (first 400 chars):
> Experts disagree on the length of the Amazon—some measurements put it at 4,345 miles (6,992 km), narrowly edging out the Nile. China's Yangtze is the ...

**Mapper reasoning**: Mentions that the Amazon narrowly edges out the Nile according to some measurements, and that the Yangtze is also a major river, providing context for river lengths.

| Field | Value |
|-------|-------|
| Mapper relationship | `context` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-e3_4_2bd08f08 -> `context`

**Is the Amazon or the Nile the Longest Reiver in the World? Depends ...** (voronoiapp.com, unclassified/unclassified)
URL: https://www.voronoiapp.com/nature/-Is-the-Amazon-or-the-Nile-the-Longest-Reiver-in-the-World-Depends-Who-You-Ask-7113

**Mapper saw** (first 400 chars):
> While there is a consensus on the Nile being the longest, some experts list the Amazon's length at 4,345 miles (6,992 km), making it 300 miles (342 km) longer ...

**Mapper reasoning**: Discusses the debate between the Nile and Amazon being the longest, providing context for the comparison.

| Field | Value |
|-------|-------|
| Mapper relationship | `context` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-e3_1_c8bb72da -> `supports`

**The world's longest rivers, ranked by length. The Nile or the Amazon ...** (facebook.com, unclassified/unclassified)
URL: https://www.facebook.com/fromquarktoquasars/posts/the-worlds-longest-rivers-ranked-by-lengththe-nile-or-the-amazon-scientists-stil/1415753193495942/

**Mapper saw** (first 400 chars):
> The #Amazon River is 6,992.06 kilometers long, originating at the foot of Mount Mismi in Peru and flowing into the Atlantic Ocean in Brazil. For centuries, the ...

**Mapper reasoning**: States the Amazon River is 6,992.06 kilometers long, and the title of the evidence suggests it is the longest.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-rec-e2_3_da2a6aff -> `supports`

**and even more in floodplains. 5️⃣ Extraordinary ... - Facebook** (facebook.com, unclassified/unclassified)
URL: https://www.facebook.com/geography01/posts/-amazon-riverthe-amazon-river-is-one-of-the-most-impressive-rivers-on-earth-loca/1189438023347879/

**Mapper saw** (first 400 chars):
> The Amazon River is the longest and largest river in the world, surpassing the Nile, with a length of approximately 7,000 kilometers. It rises in the Peruvian ...

**Mapper reasoning**: States the Amazon River is the longest and largest river in the world, surpassing the Nile.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### State judgment: `disputed`

Ref tally: 2 supports, 3 challenges, 2 context

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

- **ev-f1d845015a49**: Brazil and the Amazon: 50 Years of Shifting Policy & Global Impact (visionofhumanity.org)
  > The results were dramatic: deforestation plummeted from 27,772 km² in 2004 to 4,571 km² in 2012. Brazil was hailed as the world's leader in reducing g

- **ev-15cc7d944772**: Deforestation is drying out the Amazon rainforest faster than ... - Reddit (reddit.com)
  > Brazilian Amazon deforestation peaked around 2004 at approximately 27,000 km²/year before falling dramatically by roughly 80% to 4,500-7,000 km²/year 

- **ev-96d053925705**: Deforestation and economic growth in the Amazon region (ecologyandsociety.org)
  > The Climate Institute, Washington, D. com/uploads/1/7/8/5/17857089/deforestation_and_climate_change. Deforestation and forest degradation in the Amazo

- **ev-f69b3762444b**: Deforestation in the Brazilian Amazon has fallen again in 2025 (hannahritchie.substack.com)
  > Deforestation in the Brazilian Amazon has fallen again in 2025 Progress on deforestation, but increased threats from wildfires. This year, 5,800 squar

- **ev-5cb964f28c56**: Nature Crime Fuels Deforestation in the Amazon - WRI.org (wri.org)
  > Fires in the Amazon are largely started by arson1 and related criminal activity accompanying agriculture, logging, mining and road building. In fact, 

- **ev-80e9fdc1de64**: Fires Archives - MAAP - The Monitoring of the Andes Amazon Program (maapprogram.org)
  > There is also a strong link between deforestation and fire in the Bolivian Amazon. While deforestation often precedes fires, as in Brazil, there is al

- **ev-d3d9b2970ab4**: Is the Amazon rainforest moving towards a tipping point? - Bon Pote (bonpote.com)
  > NB: answering the question “who owns the Amazon. ” is not the subject of this article, but if you are interested, here is a very well done video. Effe

- **ev-d7276b4db5ca**: Deforestation in the Amazon Rainforest - Ballard Brief (ballardbrief.byu.edu)
  > Deforestation in the Amazon Rainforest + Summary Deforestation in the Amazon rainforest represents a critical issue in our modern world, as it is the 

- **ev-87cf7cd86007**: Deforestation of the Amazon rainforest (Wikipedia)
  > The Amazon rainforest, spanning an area of 3,000,000 km2, is the world's largest rainforest. It encompasses the largest and most biodiverse tropical r

- **ev-dccbda7630c0**: Deforestation in Brazil (Wikipedia)
  > Brazil once had the highest deforestation rate in the world, and recent data still shows high rates of deforestation. Between 2001 and 2023, Brazil lo

- **ev-2e55b9cd2b63**: Deforestation (Wikipedia)
  > Deforestation or forest clearance is the removal and destruction of a forest or stand of trees from land that is then converted to non-forest use. Def

- **ev-b647f748768c**: Deforestation by continent (Wikipedia)
  > Rates and causes of deforestation vary from region to region around the world. In 2009, two-thirds of the world's forests were located in just 10 coun

- **ev-cf0147c2ba6d**: Amazon rainforest (Wikipedia)
  > The Amazon rainforest, also called the Amazon jungle or Amazonia, is a moist broadleaf tropical rainforest in the Amazon biome that covers most of the

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
