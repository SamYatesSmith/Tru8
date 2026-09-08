# Unfamiliar real-source pilot — 2026-09-08

This is a small acceptance pilot following the SQLite work. The application code and candidate prompts were frozen at `ad8edab` during evaluation. It is not the original plan's larger representative benchmark or an 8/10 product re-score.

## Preregistered cases and captures

Selected primary documents not used in the preceding candidate tuning:

- [PostgreSQL 18 serialization failure handling](https://www.postgresql.org/docs/18/mvcc-serialization-failure-handling.html): full-transaction retry, no guarantee of completion on the next attempt, and an unsupported latency bound.
- [NASA seasons explanation](https://spaceplace.nasa.gov/seasons/en/): axial tilt, the incorrect closest-to-Sun summer explanation, and an unsupported local forecast.
- [NOAA weather versus climate](https://www.ncei.noaa.gov/news/weather-vs-climate): long-term climate, limits of Climate Normals for daily detail, and an unsupported rain forecast.
- [USGS earthquake prediction](https://www.usgs.gov/faqs/can-you-predict-earthquakes): planned but not executed. Direct acquisition yielded an empty response; retrying the publicly indexed URL returned HTTP 202 with zero bytes. Web search could read the page, but no usable direct capture was substituted or invented.

Expected source/element relationships were saved in `backend/tests/evaluation/passage_quality/real_source_pilot.json` before model execution. Document bytes and extracted text were frozen and hashed before either arm ran. Captured text lengths were 2,966 / 3,945 / 5,698 characters; this pilot does not test long-document truncation. Text preparation used a simple controlled BeautifulSoup main/article/body extraction, not the application's HTML extractor. Each case uses one fixed, manually primary-labelled source and three fixed elements. Retrieval, classification, decomposition and multi-source competition are not measured.

## Harness correction, not a quality gain

The first run used the generic evidence ID `source`. All default references disappeared. A separate raw-response diagnostic showed that the model supplied the document title instead of this ID, so strict reference validation discarded otherwise sensible relationships. The candidate's later pair review then appeared to create a large improvement. This comparison was rejected as unrepresentative of production identifiers.

Both arms were rerun with production-shaped IDs (`ev-` plus a URL digest), using identical source bytes, expected answers, models and case order. Initial results remain at `tmp/real-source-pilot`; the diagnostic is `tmp/real-source-control-response.json`. Valid comparison: `tmp/real-source-pilot-production-ids`. No application parser was relaxed and no source was promoted to force a pass.

## Valid comparison

Default/candidate/candidate/default for each of three available documents: twelve complete distillation-plus-mapping runs. All 36 predeclared relationship checks passed: 18/18 default, 18/18 candidate. Each version preserved all six expected supports and six expected challenges across repeats. For six unestablished claims per version, neither invented support or challenge. Both left all six context relationships unmapped; these omissions are counted separately and are not evidence of complete contextual coverage.

This shows no regression on these three relatively short single-source documents. It does not show a candidate advantage, demonstrate high recall, resolve the USGS acquisition failure, or justify activation. Earlier synthetic context omissions and broader real-source coverage remain relevant.

Tracked results and capture hashes: `backend/tests/evaluation/passage_quality/real_source_pilot_results.json`. The valid run used 30 model requests and 296,623 request characters. No runtime changes, model changes, persistent flag activation or deployment. Full replay matched 185 ok / 1 warn / 13 known fail / 2 unexercised with no cassette drift (`tmp/quality-replay-real-source-pilot.log`). No goldens or cassettes changed.

## Next gate

Extend acceptance to longer, competing and time-qualified real-source evidence under fixed inputs, and assess completed reports with the original rubric. Keep acquisition failures and uninspected evidence visible. Decomposition/source independence, PDF pagination and browser/operational acceptance remain open. The candidate remains disabled; the user's 8/10 minimum is not yet demonstrated.
