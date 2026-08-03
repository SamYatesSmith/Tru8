# case-012 — Review Sheet

**Claim**: Sixty percent of the Amazon rainforest is located within the borders of Brazil.
**Type**: empirical | **Model**: gemini-2.5-flash-lite | **Prompt hash**: `42d34cb9117b`

## Elements

- **e1**: The total area of the Amazon rainforest can be quantified.
- **e2**: The area of the Amazon rainforest located within Brazil can be quantified.
- **e3**: The proportion of the Amazon rainforest within Brazil is 60% of the total area.

---

## e1 — mapper state: `supported`

### ev-468bdec07380 -> `supports`

**Amazon Rainforest Facts - One Tree Planted** (onetreeplanted.org, commentary/data)
URL: https://onetreeplanted.org/blogs/stories/amazon-rainforest-facts?srsltid=AfmBOoragbvmnNcQc8onprBbKq_tS6s7wAeXEgZbkRv5Qg99w_q72_qb

**Mapper saw** (first 400 chars):
> Covering an area of approximately 2. 3 million square miles (6 million square kilometers), it's home to the world's largest rainforest. As a whole, the Amazon Biome covers about 40% of the continent of South America. The Amazon River is the world's largest river by volume of flow and size of the drainage basin. Covering at least 4,000 miles, it carries the largest volume of freshwater on Earth—abo

**Beyond window** (+39 chars):
> ut 20% of the world's liquid freshwater

**Mapper reasoning**: States the Amazon covers an area of approximately 2.3 million square miles (6 million square kilometers).

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `___` (true/false) |
| Notes | |

### ev-b957bf967a43 -> `supports`

**Amazon Rainforest - Plants, Animals, Climate, & ...** (britannica.com, commentary/analysis)
URL: https://www.britannica.com/place/Amazon-Rainforest

**Mapper saw** (first 400 chars):
> In the 20th century, Brazil’s rapidly growing population settled major areas of the Amazon Rainforest. The size of the Amazon forest shrank dramatically as a result of settlers’ clearance of the land to obtain lumber and to create grazing pastures and farmland. Brazil holds approximately 60 percent of the Amazon basin within its borders, and some 1,583,000 square miles (4,100,000 square km) of thi

**Beyond window** (+403 chars):
> s was covered by forests in 1970. The amount of forest cover declined to some 1,283,000 square miles (3,323,000 square km) by 2016, about 81 percent of the area that had been covered by forests in 1970. In the 1990s the Brazilian government and various international bodies began efforts to protect parts of the forest from human encroachment, exploitation, deforestation, and other forms of destruction

**Mapper reasoning**: Mentions 'some 1,583,000 square miles (4,100,000 square km) of this' referring to the Amazon basin within Brazil, implying a total area can be quantified.

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

### ev-b957bf967a43 -> `supports`

**Amazon Rainforest - Plants, Animals, Climate, & ...** (britannica.com, commentary/analysis)
URL: https://www.britannica.com/place/Amazon-Rainforest

**Mapper saw** (first 400 chars):
> In the 20th century, Brazil’s rapidly growing population settled major areas of the Amazon Rainforest. The size of the Amazon forest shrank dramatically as a result of settlers’ clearance of the land to obtain lumber and to create grazing pastures and farmland. Brazil holds approximately 60 percent of the Amazon basin within its borders, and some 1,583,000 square miles (4,100,000 square km) of thi

**Beyond window** (+403 chars):
> s was covered by forests in 1970. The amount of forest cover declined to some 1,283,000 square miles (3,323,000 square km) by 2016, about 81 percent of the area that had been covered by forests in 1970. In the 1990s the Brazilian government and various international bodies began efforts to protect parts of the forest from human encroachment, exploitation, deforestation, and other forms of destruction

**Mapper reasoning**: States that Brazil holds approximately 60 percent of the Amazon basin within its borders and quantifies this as 'some 1,583,000 square miles (4,100,000 square km)'.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `___` (true/false) |
| Notes | |

### ev-3d32c0cd4676 -> `supports`

**The Amazon by the Numbers** (americasquarterly.org, commentary/data)
URL: https://americasquarterly.org/article/amazon-numbers/

**Mapper saw** (first 400 chars):
> It covers 59% of Brazil and includes the states of Acre, Amapá, Amazonas, Mato Grosso, Pará, Rondônia, Roraima, Tocantins, and more than half of Maranhão.

**Mapper reasoning**: States the Amazon covers 59% of Brazil and lists the states included, quantifying the portion within Brazil.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
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

## e3 — mapper state: `disputed`
*Uncertainty*: One piece of evidence states 'About 60%' and another states 'approximately 60 percent', while a third states '59%', indicating a slight discrepancy.

### ev-10f060cef63d -> `supports`

**About 60% of the entire Amazon rainforest lies in Brazil : r/MapPorn** (reddit.com, commentary/data)
URL: https://www.reddit.com/r/MapPorn/comments/1pu4q43/about_60_of_the_entire_amazon_rainforest_lies_in/

**Mapper saw** (first 400 chars):
> About 60% of the entire Amazon rainforest lies in Brazil · Comments Section · More posts you may like.

**Mapper reasoning**: Directly states 'About 60% of the entire Amazon rainforest lies in Brazil'.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### ev-b957bf967a43 -> `supports`

**Amazon Rainforest - Plants, Animals, Climate, & ...** (britannica.com, commentary/analysis)
URL: https://www.britannica.com/place/Amazon-Rainforest

**Mapper saw** (first 400 chars):
> In the 20th century, Brazil’s rapidly growing population settled major areas of the Amazon Rainforest. The size of the Amazon forest shrank dramatically as a result of settlers’ clearance of the land to obtain lumber and to create grazing pastures and farmland. Brazil holds approximately 60 percent of the Amazon basin within its borders, and some 1,583,000 square miles (4,100,000 square km) of thi

**Beyond window** (+403 chars):
> s was covered by forests in 1970. The amount of forest cover declined to some 1,283,000 square miles (3,323,000 square km) by 2016, about 81 percent of the area that had been covered by forests in 1970. In the 1990s the Brazilian government and various international bodies began efforts to protect parts of the forest from human encroachment, exploitation, deforestation, and other forms of destruction

**Mapper reasoning**: States Brazil holds approximately 60 percent of the Amazon basin within its borders.

| Field | Value |
|-------|-------|
| Mapper relationship | `supports` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `___` (true/false) |
| Notes | |

### ev-3d32c0cd4676 -> `challenges`

**The Amazon by the Numbers** (americasquarterly.org, commentary/data)
URL: https://americasquarterly.org/article/amazon-numbers/

**Mapper saw** (first 400 chars):
> It covers 59% of Brazil and includes the states of Acre, Amapá, Amazonas, Mato Grosso, Pará, Rondônia, Roraima, Tocantins, and more than half of Maranhão.

**Mapper reasoning**: States the Amazon covers 59% of Brazil, which is very close but not exactly 60%.

| Field | Value |
|-------|-------|
| Mapper relationship | `challenges` |
| Correct? | `___` (true/false) |
| Expected relationship | `___` (supports/challenges/context) |
| Failure mode | `___` (A/B/C/D/—) |
| Window sufficient? | `likely` (true/false) |
| Notes | |

### State judgment: `disputed`

Ref tally: 2 supports, 1 challenges, 0 context

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

- **ev-154ac72500ce**: In 2025, deforestation fell by 11.08 percent in the Amazon ... (gov.br)
  > Notícias COMBATING DEFORESTATION In 2025, deforestation fell by 11. 08 percent in the Amazon and by 11. 49 percent in the Cerrado A stretch of forest 

- **ev-8c1d6248751b**: Brazil's Amazon lost area the size of Spain in 40 years: study (ctvnews.ca)
  > Brazil’s Amazon lost area the size of Spain in 40 years: study Published: Here Are The 60 Best Advent Calendars For 2025 You Can Get In Canada (So Far

- **ev-fe5bca72e16f**: Revealing the Amazon Rainforest Map Through Geography ... (puertomaldonadotours.com)
  > Though originating in Peru, the river’s identity as the Amazon is most prominently mapped within Brazilian territory, where it expands into a web of o

- **ev-3ae582654297**: Brazilian Amazon on Track for Record Low Deforestation - Yale E360 (e360.yale.edu)
  > The water needed to feed a single soybean crop is equal to the output of roughly 18 square feet of rainforest, and each bit of rainforest cleared has 

- **ev-e4684bb7246f**: Leaders Back Tropical Forests Fund at Bogotá Summit - OTCA (otca.org)
  > 2 billion hectares of tropical forests distributed across the Amazon, the Congo Basin, and Southeast Asia, ecosystems that are being affected by uncon

- **ev-7b5e58fd328d**: Safeguarding biodiversity in the Amazon – key to ... (un-redd.org)
  > ©UNDP Brazil/ Leonardo Dall’Igna The Amazon rainforest is one of Earth’s most biodiverse ecosystems, home to a staggering variety of plant and animal 

- **ev-6a05af64b0f3**: Tropical forests of the Americas (tropicalforesters.org)
  > Distribution and Characteristics - Distribution：Rainforest are mainly distributed in Amazon basin in south America. Its rainforest area accounts for a

- **ev-92a5c852c18b**: Review for "Simulated sensitivity of the Amazon rainforest to extreme drought" (CrossRef)
  > Academic research: Review for "Simulated sensitivity of the Amazon rainforest to extreme drought"

- **ev-4153c1e779d7**: Rainforest Guardians and Sustainable Development (CrossRef)
  > Academic research: Rainforest Guardians and Sustainable Development

- **ev-437180d343b5**: A DATA DRIVEN APPROACH TO STUDYING THE AMAZON RAINFOREST OF BRAZIL (CrossRef)
  > Academic research: A DATA DRIVEN APPROACH TO STUDYING THE AMAZON RAINFOREST OF BRAZIL

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
