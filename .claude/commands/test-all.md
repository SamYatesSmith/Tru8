Run the full backend test suite and report results.

```bash
cd backend && pytest tests/ -v --tb=short 2>&1
```

If tests fail, summarize: how many passed, how many failed, and list the failing test names with one-line error descriptions.
