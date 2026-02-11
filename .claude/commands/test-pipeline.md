Run the backend pipeline unit tests and report results.

```bash
cd backend && pytest tests/unit/pipeline/ -v --tb=short 2>&1
```

If any tests fail, read the failing test file and the source file it tests, then explain what broke and why.
