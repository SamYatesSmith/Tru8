# Five flagged items: the full text the labeller saw (up to 1,200 chars)

## #17 `h217` www.transportenvironment.org
- **URL:** https://www.transportenvironment.org/articles/how-clean-are-electric-cars
- **Title:** How clean are electric cars?
- **Input kind:** start0_window

```text
How clean are electric cars? How much CO2 can electric cars really save compared to diesel and petrol cars? To answer this question we have developed a tool that compiles all the most up-to-date data on CO2 emissions linked to the use of an electric, diesel or petrol car. We have taken into account all possible criteria such as the amount of CO2 emitted when electricity is produced or fuel is burnt, as well as the carbon impact of resource extraction for batteries or of building a power plant. We have found out that electric cars in Europe emit, on average, more than 3 times less CO2 than equivalent petrol cars. Lead expert In the worst case scenario, an electric car with a battery produced in China and driven in Poland still emits 37% less CO2 than petrol. And in the best case scenario, an electric car with a battery produced in Sweden and driven in Sweden can emit 83% less than 
```

## #19 `h094` sqlite.org
- **URL:** https://sqlite.org/forum/forumpost/94c40d994adfb697?t=c&unf
- **Title:** SQLite User Forum: wal checkpointing very slow
- **Input kind:** start0_window

```text
> In WAL mode, until you reach a checkpoint, SQLite doesn't update the database. All changes are logged in the WAL file. When a checkpoint is processed, SQLite has to go through the log of changes, figure out which ones haven't been obsoleted by later changes, and make appropriate changes to the database file. Then it can start again with a new blank WAL file. Partially correct. When write-ahead logging is in effect, pages changed by each transaction are written to the write-ahead log. This means that even though a "transaction" may only affect one itty bitty row, it may impact multiple database pages (the page(s) containing the data and any pages containing btree or index data related to the table). This means that a "small update to one row" may result in "a shitload of changed pages". Each shitload is a separate set of changes (transaction). So a "whole bunch of small transactions" 
```

## #22 `h057` lists.opensuse.org
- **URL:** https://lists.opensuse.org/archives/list/factory@lists.opensuse.org/latest?count=200&page=3
- **Title:** openSUSE Factory
- **Input kind:** stored_snippet

```text
... version 3.51.3: * Fix the WAL-reset database corruption bug: https://sqlite.org/wal.html#walresetbug * Other minor bug fixes. ==== systemsettings6 ==== Version ...
```

## #28 `h042` github.com
- **URL:** https://github.com/Agoric/agoric-sdk/issues/7069
- **Title:** remove the explicit wal_checkpoint(FULL) · Issue #7069 · Agoric/agoric-sdk
- **Input kind:** start0_window

```text
- Notifications You must be signed in to change notification settings - Fork 255 - remove the explicit wal_checkpoint(FULL) #7069 Description What is the Problem Being Solved? The current swingstore DB code uses WAL mode, with synchronous=FULL: agoric-sdk/packages/swing-store/src/swingStore.js Lines 203 to 204 in 40dc287 and then during commit(), it does both a DB COMMIT and a wal_checkpoint(FULL): agoric-sdk/packages/swing-store/src/swingStore.js Lines 517 to 529 in 40dc287 When SQLite is in WAL mode, it records new changes in the separate .wal file, and then periodically does a "checkpoint" to merge these changes back into the main .sqlite file. Read performance is slightly degraded if the WAL file gets too large (readers must look in two places to make sure they're seeing all potential writes), and that only gets fixed by the checkpoint operation. By default, SQLite performs a 
```

## #30 `h064` nhsjs.com
- **URL:** https://nhsjs.com/2022/a-comparison-of-the-environmental-consequences-in-the-production-and-disposal-phases-of-lithium-ion-batteries-and-gasoline/
- **Title:** A Comparison of the Environmental Consequences in the Production and Disposal Phases of Lithium-Ion Batteries and Gasoline - NHSJS
- **Input kind:** start0_window

```text
Audrey Wen, Min-seung Kang, James Truncer Abstract Gasoline is recognized as an unsustainable energy source, and multiple industries now use lithium-ion battery alternatives to meet society’s demands for a shift away from nonrenewable sources. Lithium-ion battery powered products produce zero emissions and no toxic fumes, so they are deemed more eco-friendly than their gas counterparts. Yet, such a conclusion disregards the other environmental costs present in the earlier and later stages of the battery life cycle. The process of mining lithium and cobalt for lithium-ion batteries and the difficulties of recycling such materials should be taken into account just as the process of extracting gasoline from crude oil and the pollution from exhaust gases are. This study provides a comparison of lithium-ion batteries and gasoline as energy sources in the production and disposal phases from 
```
