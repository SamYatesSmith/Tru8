# Review sheet — t07_sqlite_busy

Check `00a19ec2-1531-435a-8c52-ee059f14e852` · 57 s · 15 sources. Input: {"input_type": "text", "content": "In SQLite, write-ahead logging means readers never block writers, therefore SQLITE_BUSY errors cannot occur.", "url": null, "file_path": null, "user_query": null}

For each **directional label** below answer: **Justified?** Y / N / Unsure. If N, the kind: `direction` (the source says the opposite) · `absent` (the source does not say this) · `scope` (different population / period / place / endpoint / study) · `recital` (the source only repeats the claim) · `other` (say what). One line of note when you mark N or Unsure.

## Claim 1: In SQLite, write-ahead logging means readers never block writers, therefore SQLITE_BUSY errors cannot occur.

### Element 1 — state: **supported**

> Enabling write-ahead logging in SQLite completely eliminates reader-to-writer and writer-to-reader blocking.

#### t07_sqlite_busy/c1/e1/ev-296b8fe725bc

- **Label:** `supports` · **Source:** [SQLite WAL Internals Explained for Developers](https://www.sqliteforum.com/p/sqlite-wal-internals-frames-commits) · sqliteforum.com · tier `commentary` · type `analysis`
- **System's reasoning:** Confirms that in WAL mode, a writer operates without blocking readers and readers do not block the writer.
- **What the mapper was given (distilled facts or snippet):** - WAL stands for Write-Ahead Logging. - In WAL mode, multiple readers can run simultaneously. - In WAL mode, a single writer operates without blocking readers. - In WAL mode, readers do not block the writer. - WAL mode only allows one writer at a time.
- **Justified?** ☐ Y ☐ N ☐ Unsure · **Kind:** ______ · **Note:** ________________________________

#### t07_sqlite_busy/c1/e1/ev-6f010fe465d3

- **Label:** `supports` · **Source:** [Reddit](https://www.reddit.com/r/learnprogramming/comments/1l82ohn/confused_about_sqlite_and_concurrency/) · reddit.com · tier `commentary` · type `opinion`
- **System's reasoning:** States that readers and writers do not block each other in WAL mode.
- **What the mapper was given (distilled facts or snippet):** readers and writers do not block each other any more, and reading doesn't block other readers
- **Justified?** ☐ Y ☐ N ☐ Unsure · **Kind:** ______ · **Note:** ________________________________

#### t07_sqlite_busy/c1/e1/ev-452faa47894f

- **Label:** `supports` · **Source:** [What to do about SQLITE_BUSY errors despite setting a timeout - Bert Hubert's writings](https://berthub.eu/articles/posts/a-brief-post-on-sqlite3-database-locked-despite-timeout/) · berthub.eu · tier `commentary` · type `analysis`
- **System's reasoning:** Notes SQLite's concurrency promise in WAL mode that readers do not block writers and a writer does not block readers.
- **What the mapper was given (distilled facts or snippet):** - When running in WAL mode, SQLite makes concurrency promises that readers do not block writers and a writer does not block readers. - If you leave a transaction open for too long, the other side will get a SQLITE_BUSY error. - If you later in a read-only transaction try to write to the database somehow, SQLite will attempt to upgrade your transaction to a write transaction. - When the transaction on the left wanted to upgrade itself to a read-write transaction, SQLite could not allow this since the transaction on the right might already have made changes that the transaction on the left had not yet seen.
- **Justified?** ☐ Y ☐ N ☐ Unsure · **Kind:** ______ · **Note:** ________________________________

#### t07_sqlite_busy/c1/e1/ev-52694c1c64a1

- **Label:** `supports` · **Source:** [The Current State Of SQLite Persistence On The Web: May 2026 Update](https://powersync.com/blog/sqlite-persistence-on-the-web) · powersync.com · tier `commentary` · type `analysis`
- **System's reasoning:** Explains that WAL journal mode allows read transactions to execute concurrently with a write transaction.
- **What the mapper was given (distilled facts or snippet):** - When using the WAL journal mode instead, the concurrency restrictions are relaxed somewhat: read transactions can be executed concurrently with a single write transaction. - This works by appending changes to a log file, readers can consult that log (up to the offset active when the read transaction was started) without conflicts.
- **Justified?** ☐ Y ☐ N ☐ Unsure · **Kind:** ______ · **Note:** ________________________________

#### t07_sqlite_busy/c1/e1/ev-35c130f56f3f

- **Label:** `supports` · **Source:** [SQLite: enable WAL mode and busy_timeout for concurrent write performance · Issue #907 · cashubtc/nutshell](https://github.com/cashubtc/nutshell/issues/907) · github.com · tier `primary` · type `official_statement`
- **System's reasoning:** Confirms that setting PRAGMA journal_mode=WAL allows concurrent reads during writes.
- **What the mapper was given (distilled facts or snippet):** - The default SQLite journal mode (delete) serializes all writes and readers block on writers. - Using PRAGMA journal_mode=WAL allows concurrent reads during writes. - Using PRAGMA busy_timeout=5000 waits for locks at the driver level instead of failing immediately.
- **Justified?** ☐ Y ☐ N ☐ Unsure · **Kind:** ______ · **Note:** ________________________________

<details><summary>Context only (not graded; flag here if one of these should have been directional)</summary>

- builder.ai2sql.io — SQLite Error: Database Is Locked (Fix Guide) — _Confirms that enabling WAL mode stops readers from blocking the writer._

</details>

<details><summary>Set aside by the system's mechanical rules (flag here if a rule fired wrongly)</summary>

- builder.ai2sql.io was read as `supports`, set aside as context: a copy of a source already counted

</details>

### Element 2 — state: **disputed**

> The absence of reader-writer blocking makes it impossible for any operation to trigger an SQLITE_BUSY error under write-ahead logging.

#### t07_sqlite_busy/c1/e2/ev-d545fde7c51e

- **Label:** `challenges` · **Source:** [Runnable SQLite Docs: WAL & Concurrency | Coddy](https://coddy.tech/docs/sqlite/wal-mode-and-concurrency) · coddy.tech · tier `commentary` · type `analysis`
- **System's reasoning:** Demonstrates that SQLite still serializes writes in WAL mode and raises SQLITE_BUSY if two connections attempt to write at the same time.
- **What the mapper was given (distilled facts or snippet):** - By default, SQLite uses a rollback journal where writers and readers fight for the same file. - In WAL mode, a writer and any number of readers can be active at the same moment. - SQLite still serializes writes, meaning at any moment, exactly one transaction holds the write lock. - If two connections both try to write at the same time, the second one gets SQLITE_BUSY. - Setting a busy timeout, such as busy_timeout=5000, tells SQLite to wait up to 5 seconds for a lock before raising an error.
- **Justified?** ☐ Y ☐ N ☐ Unsure · **Kind:** ______ · **Note:** ________________________________

#### t07_sqlite_busy/c1/e2/ev-5a70701234a8

- **Label:** `challenges` · **Source:** [Result and Error Codes](https://sqlite.org/rescode.html) · sqlite.org · tier `primary` · type `data`
- **System's reasoning:** Explains that SQLITE_BUSY occurs whenever a transaction attempts to write while another write transaction is in progress.
- **What the mapper was given (distilled facts or snippet):** - The SQLITE_BUSY result code indicates that the database file could not be written or read because of concurrent activity by some other database connection, usually in a separate process. - Process B will get back an SQLITE_BUSY result if process A is in the middle of a large write transaction and process B attempts to start a new write transaction, because SQLite only supports one writer at a time. - The sqlite3_busy_timeout() and sqlite3_busy_handler() interfaces and the busy_timeout pragma are available to help deal with SQLITE_BUSY errors. - An SQLITE_BUSY error can occur at any point in a transaction: when first started, during write or update operations, or when the transaction commits. - The BEGIN IMMEDIATE command might itself return SQLITE_BUSY, but if it succeeds, SQLite guarantees no subsequent operations on the same database through the next COMMIT will return SQLITE_BUSY. …
- **Justified?** ☐ Y ☐ N ☐ Unsure · **Kind:** ______ · **Note:** ________________________________

### Element 3 — state: **disputed**

> Writer-to-writer concurrency conflicts, which can still generate SQLITE_BUSY errors in write-ahead logging mode, do not occur or are irrelevant.

#### t07_sqlite_busy/c1/e3/ev-d8d272177c2b

- **Label:** `challenges` · **Source:** [In SQLite, transactions by default start in “deferred” mode. This means they do ... | Hacker News](https://news.ycombinator.com/item?id=45781519) · news.ycombinator.com · tier `commentary` · type `opinion`
- **System's reasoning:** Notes that only one writer is allowed at a time in WAL mode and write lock contention triggers SQLITE_BUSY errors.
- **What the mapper was given (distilled facts or snippet):** - You get SQLITE_BUSY when transaction #1 starts in read mode, transaction #2 starts in write mode, and then transaction #1 attempts to upgrade from read to write mode while transaction #2 still holds the write lock. - In WAL mode, writers and readers don’t interfere with each other, so you can still do pure read queries in parallel. - Only one writer is allowed at a time no matter what, so writers queue up and you have to take the write lock at some point anyway.
- **Justified?** ☐ Y ☐ N ☐ Unsure · **Kind:** ______ · **Note:** ________________________________

#### t07_sqlite_busy/c1/e3/ev-ff66f2f5502e

- **Label:** `challenges` · **Source:** [Reddit](https://www.reddit.com/r/golang/comments/1exk981/sqlite_database_is_locked_with_wal_mode/) · reddit.com · tier `commentary` · type `opinion`
- **System's reasoning:** Explicitly confirms that writers conflict with other writers in WAL mode.
- **What the mapper was given (distilled facts or snippet):** In WAL mode , writers only conflict with other writers
- **Justified?** ☐ Y ☐ N ☐ Unsure · **Kind:** ______ · **Note:** ________________________________

#### t07_sqlite_busy/c1/e3/ev-4c0379fc2c14

- **Label:** `challenges` · **Source:** [SQLite concurrent writes and "database is locked" errors](https://tenthousandmeters.com/blog/sqlite-concurrent-writes-and-database-is-locked-errors/) · tenthousandmeters.com · tier `commentary` · type `analysis`
- **System's reasoning:** States that concurrent write transactions can fail with database locked errors even in WAL mode due to the single-writer limit.
- **What the mapper was given (distilled facts or snippet):** - SQLite handles concurrent writes with a global write lock allowing only one writer at a time. - If you have many concurrent write transactions, some will take a long time and some may even fail with the 'database is locked' error. - Both rollback mode and WAL mode allow multiple parallel readers and both allow one writer at a time. - WAL mode supports having readers simultaneously with a writer, while in rollback mode, writers and readers block each other.
- **Justified?** ☐ Y ☐ N ☐ Unsure · **Kind:** ______ · **Note:** ________________________________

#### t07_sqlite_busy/c1/e3/ev-302b4841bc95

- **Label:** `challenges` · **Source:** [SQLite in Production - A Real-World Benchmark](https://shivekkhurana.com/blog/sqlite-in-production/) · shivekkhurana.com · tier `commentary` · type `analysis`
- **System's reasoning:** Notes that SQLite fails with lock errors as soon as write concurrency exceeds one.
- **What the mapper was given (distilled facts or snippet):** - Out of the box, SQLite starts failing as soon as write concurrency exceeds one. - Setting PRAGMA busy_timeout instructs the connection to retry for a specified duration before throwing a lock error. - Increasing the busy timeout prevents lock errors without affecting latency. - SQLite's Write-Ahead Logging (WAL) mode allows writers to append sequentially and readers never block on writers.
- **Justified?** ☐ Y ☐ N ☐ Unsure · **Kind:** ______ · **Note:** ________________________________
