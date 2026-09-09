# Review sheet — t09_sqlite_url

Check `6fc1ddb2-264e-4517-9bc1-1853505d1e06` · 88 s · 52 sources. Input: {"input_type": "url", "content": null, "url": "https://www.sqlite.org/wal.html", "file_path": null, "user_query": null}

For each **directional label** below answer: **Justified?** Y / N / Unsure. If N, the kind: `direction` (the source says the opposite) · `absent` (the source does not say this) · `scope` (different population / period / place / endpoint / study) · `recital` (the source only repeats the claim) · `other` (say what). One line of note when you mark N or Unsure.

## Claim 1: SQLite introduced the Write-Ahead Log option beginning with version 3.7.0 on July 21, 2010

### Element 1 — state: **supported**

> SQLite introduced the Write-Ahead Log option starting with version 3.7.0.

#### t09_sqlite_url/c1/e1/ev-e68b3db1d678

- **Label:** `supports` · **Source:** [SQLite enables Write-Ahead Log journal (WAL) by default](https://www.drupal.org/node/2769027) · drupal.org · tier `primary` · type `official_statement`
- **System's reasoning:** Confirms that support for WAL in SQLite is available starting from version 3.7.0.
- **What the mapper was given (distilled facts or snippet):** - Support for WAL on SQLite is available from version 3.7.0.
- **Justified?** ☐ Y ☐ N ☐ Unsure · **Kind:** ______ · **Note:** ________________________________

#### t09_sqlite_url/c1/e1/ev-db950fc9865f

- **Label:** `supports` · **Source:** [The Forensic Implications of SQLite’s Write Ahead Log](https://digitalinvestigation.wordpress.com/2012/05/04/the-forensic-implications-of-sqlites-write-ahead-log/) · digitalinvestigation.wordpress.com · tier `commentary` · type `opinion`
- **System's reasoning:** Affirms that the Write Ahead Log journaling mechanism was introduced from version 3.7.0.
- **What the mapper was given (distilled facts or snippet):** - From version 3.7.0 of the SQLite engine an alternative journal mechanism was introduced called "Write Ahead Log" (ubiquitously shortened to "WAL").
- **Justified?** ☐ Y ☐ N ☐ Unsure · **Kind:** ______ · **Note:** ________________________________

#### t09_sqlite_url/c1/e1/ev-3fe1877e9cb7

- **Label:** `supports` · **Source:** [SQLite, Version 3 - The Library of Congress](https://www.loc.gov/preservation/digital/formats/fdd/fdd000461.shtml) · loc.gov · tier `primary` · type `official_statement`
- **System's reasoning:** States that starting with version 3.7.0, SQLite has supported the write-ahead log mechanism.
- **What the mapper was given (distilled facts or snippet):** Starting with version 3.7.0, SQLite has supported an alternative mechanism, using a write-ahead log (WAL). The write-ahead log is stored ...
- **Justified?** ☐ Y ☐ N ☐ Unsure · **Kind:** ______ · **Note:** ________________________________

#### t09_sqlite_url/c1/e1/ev-rec-e2_6_1623c89e

- **Label:** `supports` · **Source:** [SQLite vs MySQL 2026: 4.9x Read Gap [Tested] - Tech Insider](https://tech-insider.org/sqlite-vs-mysql-2026/) · tech-insider.org · tier `commentary` · type `analysis`
- **System's reasoning:** States that SQLite's WAL (Write-Ahead Logging) mode was introduced in version 3.7.0, confirming the element.
- **What the mapper was given (distilled facts or snippet):** SQLite's WAL (Write-Ahead Logging) mode, introduced in version 3.7.0 and refined through the 3.53.x series – including the 3.53.0 release on April 9, 2026
- **Justified?** ☐ Y ☐ N ☐ Unsure · **Kind:** ______ · **Note:** ________________________________

<details><summary>Context only (not graded; flag here if one of these should have been directional)</summary>

- fly.io — How SQLite Scales Read Concurrency — _States that the write-ahead log (WAL) option was created in SQLite version 3.7.0 in 2010._
- sqlite-users.sqlite.narkive.com — [sqlite] WAL file size increase — _Confirms that beginning with version 3.7.0, a new Write-Ahead Log option became available._

</details>

<details><summary>Set aside by the system's mechanical rules (flag here if a rule fired wrongly)</summary>

- sqlite-users.sqlite.narkive.com was read as `supports`, set aside as context: the claimant's own organ
- fly.io was read as `supports`, set aside as context: a copy of a source already counted

</details>

### Element 2 — state: **unresolved**

> Version 3.7.0 of SQLite was released on July 21, 2010.

#### t09_sqlite_url/c1/e2/ev-rec-e2_4_159f8b0c

- **Label:** `supports` · **Source:** [Deeply buried 16-year-old SQLite bug caused last year's Tailscale ...](https://www.theregister.com/databases/2026/08/12/deeply-buried-16-year-old-sqlite-bug-caused-last-years-tailscale-outages/5287004) · theregister.com · tier `reporting` · type `news_reporting`
- **System's reasoning:** Confirms version 3.7.0 of SQLite was released in July 2010.
- **What the mapper was given (distilled facts or snippet):** SQLite maintainers believe the bug was present going all the way back to version 3.7.0, released in July 2010; it's now fixed, and the SQLite team recommends ...
- **Justified?** ☐ Y ☐ N ☐ Unsure · **Kind:** ______ · **Note:** ________________________________

<details><summary>Context only (not graded; flag here if one of these should have been directional)</summary>

- sqlite.org — SQLite Release 3.7.0 On 2010-07-21 — _Officially records that SQLite Release 3.7.0 was released on 2010-07-21._
- sqlite.org — History Of SQLite Releases — _Lists SQLite version 3.7.0 with the release date of 2010-07-21._
- sqlite.org — History Of SQLite Releases — _Lists version 3.7.0 of SQLite under the release date 2010-07-21._
- sqlite.org — C/C++ Interface For SQLite Version 3 — _States SQLite version 3.7.0 occurred on 2010-07-21._

</details>

<details><summary>Set aside by the system's mechanical rules (flag here if a rule fired wrongly)</summary>

- sqlite.org was read as `supports`, set aside as context: the claimant's own organ
- sqlite.org was read as `supports`, set aside as context: the claimant's own organ
- sqlite.org was read as `supports`, set aside as context: the claimant's own organ
- sqlite.org was read as `supports`, set aside as context: the claimant's own organ

</details>

## Claim 2: SQLite does a checkpoint automatically when the WAL file reaches a threshold size of 1000 pages by default. An SQLite database connection defaults to journal_mode equals DELETE. The PRAGMA journal_mode equals WAL setting in SQLite is persistent across closing and reopening the database.

### Element 1 — state: **supported**

> SQLite automatically performs a checkpoint when the WAL file reaches a default threshold size of 1000 pages.

#### t09_sqlite_url/c2/e1/ev-2feb7dcca39c

- **Label:** `supports` · **Source:** [remove the explicit wal_checkpoint(FULL) · Issue #7069 · Agoric/agoric-sdk](https://github.com/Agoric/agoric-sdk/issues/7069) · github.com · tier `primary` · type `data`
- **System's reasoning:** States that by default, SQLite performs an automatic checkpoint when reaching 1000 pages.
- **What the mapper was given (distilled facts or snippet):** - By default, SQLite performs a checkpoint/merge when it reaches some size (1000 pages, probably 1 or 2 MB of data).
- **Justified?** ☐ Y ☐ N ☐ Unsure · **Kind:** ______ · **Note:** ________________________________

#### t09_sqlite_url/c2/e1/ev-f3c97123d356

- **Label:** `supports` · **Source:** [SQLite Optimizations For Ultra High-Performance](https://powersync.com/blog/sqlite-optimizations-for-ultra-high-performance) · powersync.com · tier `commentary` · type `analysis`
- **System's reasoning:** Confirms that by default, WAL checkpointing occurs once the WAL exceeds 1,000 pages.
- **What the mapper was given (distilled facts or snippet):** SQLite has support for indexes on expressions and partial indexes, which may be very useful in some cases. For example, an index can be created on a field inside a JSON document using: CREATE INDEX myindex ON mytable(json_document ->> 'subfield'); # 9: Use Background WAL Checkpoints Effect: Remove the occasional fsync overhead on a transaction, typically 30-100ms. WAL checkpoints are where data is moved from the write-ahead log to the main database. This is one place that does wait synchronously for the filesystem to sync. By default, this occurs once the WAL is greater than 1,000 pages, as part of a COMMIT statement
- **Justified?** ☐ Y ☐ N ☐ Unsure · **Kind:** ______ · **Note:** ________________________________

#### t09_sqlite_url/c2/e1/ev-rec-e2_4_4c6a0432

- **Label:** `supports` · **Source:** [Runnable SQLite Docs: WAL & Concurrency - Coddy Tech](https://coddy.tech/docs/sqlite/wal-mode-and-concurrency) · coddy.tech · tier `primary` · type `analysis`
- **System's reasoning:** States that SQLite checkpoints automatically when the WAL passes approximately 1000 pages, matching the default wal_autocheckpoint.
- **What the mapper was given (distilled facts or snippet):** Checkpoints: Folding the WAL Back The WAL file can't grow forever. Checkpointing is the process of taking the committed pages in the WAL and writing them into the main database, then resetting the WAL. SQLite checkpoints automatically when the WAL passes ~1000 pages (the default wal_autocheckpoint). For most apps you can leave that alone. If you want to tune it or trigger one manually: The wal_checkpoint pragma takes a mode: PASSIVE- checkpoint as much as possible without disrupting readers/writ
- **Justified?** ☐ Y ☐ N ☐ Unsure · **Kind:** ______ · **Note:** ________________________________

<details><summary>Context only (not graded; flag here if one of these should have been directional)</summary>

- sqlite.org — Configure an auto-checkpoint — _States that new database connections default to auto-checkpointing with a threshold of 1000 pages._
- sqlite.org — SQLite User Forum: WAL File Grows Past Auto Checkpoint Limit — _Refers to the default 1000 page autocheckpoint limit in SQLite._
- sqliteforum.com — SQLite WAL Checkpoints and Performance Tuning — _Reports that SQLite triggers a checkpoint by default after roughly 1000 WAL pages accumulate._
- documentation.xojo.com — Write-Ahead logging — Xojo documentation — _Documents that SQLite automatically handles checkpoints when the WAL reaches a 1000-page threshold._
- sqlite.org — WAL-mode File Format — _Mentions that the default automatic checkpoint threshold in SQLite is 1000 pages._

</details>

<details><summary>Set aside by the system's mechanical rules (flag here if a rule fired wrongly)</summary>

- sqlite.org was read as `supports`, set aside as context: the claimant's own organ
- sqlite.org was read as `supports`, set aside as context: the claimant's own organ
- sqliteforum.com was read as `supports`, set aside as context: the claimant's own organ
- sqlite.org was read as `supports`, set aside as context: the claimant's own organ
- documentation.xojo.com was read as `supports`, set aside as context: reports the claim rather than making it — ojo documentation - According to the SQLite docs, SQLite handles checkpoints automatically

</details>

### Element 2 — state: **unresolved**

> An SQLite database connection defaults to journal_mode equals DELETE.

#### t09_sqlite_url/c2/e2/ev-267302cd92e7

- **Label:** `supports` · **Source:** [SQLite commits are not durable under default settings - blag](https://avi.im/blag/2025/sqlite-fsync/) · avi.im · tier `commentary` · type `analysis`
- **System's reasoning:** Confirms that under default settings SQLite operates in rollback journal mode and returns delete.
- **What the mapper was given (distilled facts or snippet):** - Under the default settings, SQLite operates in rollback journal mode. - According to an example output in the article, PRAGMA journal_mode returns delete by default.
- **Justified?** ☐ Y ☐ N ☐ Unsure · **Kind:** ______ · **Note:** ________________________________

#### t09_sqlite_url/c2/e2/ev-rec-e2_2_02b5f8a4

- **Label:** `supports` · **Source:** [Why is SQLite WAL mode so much faster than default DELETE ...](https://superuser.com/questions/1938008/why-is-sqlite-wal-mode-so-much-faster-than-default-delete-mode-for-concurrent-wr) · superuser.com · tier `commentary` · type `analysis`
- **System's reasoning:** States that the default journaling mode of SQLite was set to DELETE.
- **What the mapper was given (distilled facts or snippet):** The default journaling mode was set to DELETE. The write performance improved drastically, almost by a factor of 4 or 5, and the disk activity dropped ...
- **Justified?** ☐ Y ☐ N ☐ Unsure · **Kind:** ______ · **Note:** ________________________________

### Element 3 — state: **disputed**

> The PRAGMA journal_mode equals WAL setting in SQLite persists across closing and reopening the database.

#### t09_sqlite_url/c2/e3/ev-a7bbc0e5fe82

- **Label:** `supports` · **Source:** [Something I found non-obvious about WAL mode in SQLite is that it's actually a p... | Hacker News](https://news.ycombinator.com/item?id=32581375) · news.ycombinator.com · tier `commentary` · type `opinion`
- **System's reasoning:** Confirms that setting PRAGMA journal_mode=wal permanently changes the mode for that database file.
- **What the mapper was given (distilled facts or snippet):** - When you run PRAGMA journal_mode=wal; against a database file the mode is permanently changed for that file.
- **Justified?** ☐ Y ☐ N ☐ Unsure · **Kind:** ______ · **Note:** ________________________________

#### t09_sqlite_url/c2/e3/ev-e9d97aabd926

- **Label:** `supports` · **Source:** [Enabling WAL mode for SQLite database files](https://til.simonwillison.net/sqlite/enabling-wal-mode) · til.simonwillison.net · tier `commentary` · type `analysis`
- **System's reasoning:** Explains that journal_mode is persistent specifically for WAL mode across sessions.
- **What the mapper was given (distilled facts or snippet):** - According to Ben Johnson in a Hacker News comment, the journal_mode is only persistent for WAL, while the DELETE, TRUNCATE, and PERSIST modes are per-connection.
- **Justified?** ☐ Y ☐ N ☐ Unsure · **Kind:** ______ · **Note:** ________________________________

#### t09_sqlite_url/c2/e3/ev-rec-e3_6_358a01b1

- **Label:** `supports` · **Source:** [SQLite on FreeBSD: Embedded Database Review](https://freebsdsoftware.org/blog/sqlite-freebsd-review.html) · freebsdsoftware.org · tier `commentary` · type `analysis`
- **System's reasoning:** States that WAL mode is persistent once enabled and remains active until explicitly changed.
- **What the mapper was given (distilled facts or snippet):** Enable WAL mode: WAL mode is persistent -- once enabled, it remains active until explicitly changed. You only need to set it once.
- **Justified?** ☐ Y ☐ N ☐ Unsure · **Kind:** ______ · **Note:** ________________________________

#### t09_sqlite_url/c2/e3/ev-rec-e3_6_ef3318a4

- **Label:** `supports` · **Source:** [How to Install SQLite on Arch Linux - LinuxCapable](https://linuxcapable.com/how-to-install-sqlite-on-arch-linux/) · linuxcapable.com · tier `commentary` · type `analysis`
- **System's reasoning:** Confirms that WAL mode persists per database after it is enabled, remaining active after reopening the database.
- **What the mapper was given (distilled facts or snippet):** Confirm the persistent journal mode after reopening the database: wal WAL mode persists per database after it is enabled. The -wal and -shm sidecar files ...
- **Justified?** ☐ Y ☐ N ☐ Unsure · **Kind:** ______ · **Note:** ________________________________

#### t09_sqlite_url/c2/e3/ev-rec-e3_4_f0ed8242

- **Label:** `challenges` · **Source:** [Tips & Caveats - Litestream](https://litestream.io/v0.3/tips/) · litestream.io · tier `primary` · type `official_statement`
- **System's reasoning:** States that PRAGMA settings like journal_mode must be set on each database connection because they do not persist across connections.
- **What the mapper was given (distilled facts or snippet):** This pragma must be set on each database connection, as it does not persist across connections. Enabling foreign key constraints will ensure that your ...
- **Justified?** ☐ Y ☐ N ☐ Unsure · **Kind:** ______ · **Note:** ________________________________

<details><summary>Context only (not graded; flag here if one of these should have been directional)</summary>

- sqlite.org — SQLite User Forum: Using WAL mode with multiple processes — _States that WAL mode persists across multiple connections and after closing and reopening the database._

</details>

<details><summary>Set aside by the system's mechanical rules (flag here if a rule fired wrongly)</summary>

- sqlite.org was read as `supports`, set aside as context: the claimant's own organ

</details>

## Claim 3: SQLite relaxed the constraint requiring write access to read a WAL-mode database beginning with version 3.22.0 on January 22, 2018

### Element 1 — state: **contextual**

> SQLite relaxed the constraint requiring write access to read a WAL-mode database starting with version 3.22.0.

_No directional labels on this element._

<details><summary>Context only (not graded; flag here if one of these should have been directional)</summary>

- sqlite.org — SQLite Release 3.22.0 On 2018-01-22 — _Official release notes state version 3.22.0 added the ability to read WAL mode databases without write permission._
- sqlite.org — SQLite User Forum: Is it possible to make -shm/-wal files permanent? — _Notes that SQLite 3.22.0 and later allows reading a read-only WAL-mode database without -wal and -shm files._
- sqlite.org — SQLite User Forum: Is it possible to make -shm/-wal files permanent? — _Confirms that SQLite version 3.22.0 allows reading read-only WAL-mode databases._
- sqlite.org — SQLite User Forum: Need help with read only access to database — _References the read-only WAL feature introduced in SQLite version 3.22.0._
- rpmfind.net — sqlite3-3.50.4-160000.1.2.x86_64 RPM — _Provides background on earlier partial read-only capabilities in RPM changelogs requiring an existing read/write connection._

</details>

<details><summary>Set aside by the system's mechanical rules (flag here if a rule fired wrongly)</summary>

- sqlite.org was read as `supports`, set aside as context: the claimant's own organ
- sqlite.org was read as `supports`, set aside as context: the claimant's own organ
- sqlite.org was read as `supports`, set aside as context: the claimant's own organ
- sqlite.org was read as `supports`, set aside as context: the claimant's own organ

</details>

### Element 2 — state: **supported**

> Version 3.22.0 of SQLite was released on January 22, 2018.

#### t09_sqlite_url/c3/e2/ev-513ce89951c2

- **Label:** `supports` · **Source:** [SQLite 3.22 Lifecycle, EOL & Releases | CompatHub](https://compathub.com/software/sqlite/3.22) · compathub.com · tier `commentary` · type `analysis`
- **System's reasoning:** Confirms that SQLite version 3.22.0 was released on January 22, 2018.
- **What the mapper was given (distilled facts or snippet):** - SQLite version 3.22.0 was released on 22 Jan 2018.
- **Justified?** ☐ Y ☐ N ☐ Unsure · **Kind:** ______ · **Note:** ________________________________

#### t09_sqlite_url/c3/e2/ev-rec-e2_4_21824e58

- **Label:** `supports` · **Source:** [SQLite 3.53.4 - community chocolatey](https://community.chocolatey.org/packages/SQLite) · community.chocolatey.org · tier `primary` · type `data`
- **System's reasoning:** States that SQLite version 3.22.0 was approved/released on Tuesday, January 23, 2018, which conflicts slightly with the claimed January 22 date, but FreshPorts and chocolatey log entries place the release around January 22-23, 2018.
- **What the mapper was given (distilled facts or snippet):** SQLite 3.23.1, 10815, Wednesday, April 11, 2018, Approved. SQLite 3.23.0, 2547, Monday, April 2, 2018, Approved. SQLite 3.22.0, 7873, Tuesday, January 23, 2018 ...
- **Justified?** ☐ Y ☐ N ☐ Unsure · **Kind:** ______ · **Note:** ________________________________

<details><summary>Context only (not graded; flag here if one of these should have been directional)</summary>

- sqlite.org — SQLite Release 3.22.0 On 2018-01-22 — _Official release documentation states SQLite Release 3.22.0 was released on 2018-01-22._

</details>

<details><summary>Set aside by the system's mechanical rules (flag here if a rule fired wrongly)</summary>

- sqlite.org was read as `supports`, set aside as context: the claimant's own organ

</details>
