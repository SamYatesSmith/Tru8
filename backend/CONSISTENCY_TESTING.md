# Consistency Testing Guide

This guide explains how to test the Tru8 fact-checking pipeline for consistency issues and analyze diagnostic logs.

## 🎯 Purpose

The consistency test runs the same article through the fact-checking pipeline multiple times to detect non-deterministic behavior. Target: scores should be within ±5 points.

## 📋 Prerequisites

1. **Backend running** with diagnostic logging:
   ```bash
   cd backend
   uvicorn main:app --reload
   ```

2. **Query expansion enabled** in `backend/.env`:
   ```env
   ENABLE_QUERY_EXPANSION=true
   ```

3. **Python dependencies installed**:
   ```bash
   pip install httpx
   ```

## 🚀 Quick Start

### Option 1: Run with Batch Script (Windows)
```bash
cd backend
run_consistency_test.bat
```

### Option 2: Run Manually
```bash
cd backend
python test_consistency.py --runs 5 --wait 60
```

## ⚙️ Configuration Options

```bash
python test_consistency.py \
  --url "https://example.com/article" \
  --runs 5 \
  --wait 300
```

**Parameters:**
- `--url`: Article URL to test (default: East Wing article)
- `--runs`: Number of test runs (default: 5)
- `--wait`: Seconds between runs (default: 60, recommend 300 for production)

## 📊 What Gets Tested

Each run measures:
- **Overall Score** (0-100)
- **Claims Analyzed** (count)
- **Claims Supported/Uncertain/Contradicted** (breakdown)
- **Processing Time** (seconds)

## 📁 Output Files

Results saved to `consistency_test_logs/YYYYMMDD_HHMMSS/`:

```
consistency_test_logs/
└── 20251117_132845/
    ├── run_01_response.json    # Full API response
    ├── run_02_response.json
    ├── run_03_response.json
    ├── run_04_response.json
    ├── run_05_response.json
    └── summary.json            # Statistical analysis
```

## 🔍 Analyzing Results

### 1. Check Test Summary

The script automatically prints:
```
📊 CONSISTENCY ANALYSIS
==================================================

✅ Successful runs: 5/5

📈 SCORE CONSISTENCY:
   Min:      68/100
   Max:      84/100
   Average:  76.0/100
   Variance: ±16 points
   Status:   ❌ POOR (target: ±5 points)

📊 CLAIMS ANALYSIS:
   Claims analyzed:  11-11 (variance: 0)
   Claims supported: 3-6 (variance: 3)

⏱️  PROCESSING TIME:
   Min:     102.5s
   Max:     122.1s
   Average: 110.7s
```

### 2. Analyze Backend Logs

While the test runs, watch the backend console for diagnostic output:

#### ✅ **Good Signs (Consistency)**
```
🔎 QUERY RESULT  | Query: 'Trump administration East Wing demolition (site:.gov OR site:.edu...'
🔍 SEARCH RESULTS | Found: 10 results
📄 EXTRACTION | Success: 8/10 (80%)
```
Same query → Same results → Consistent

#### ❌ **Bad Signs (Non-Determinism)**
```
⏱️ BRAVE TIMEOUT | Query: 'Trump administration...'
🔎 Trying provider 2/2: SerpAPIProvider
🔍 SEARCH RESULTS | Found: 3 results  # <-- Should have been 10!
```
Timeout → Failover → Different results

### 3. Common Patterns to Look For

#### Pattern A: Query Variance
**Symptom**: Different `🔎 QUERY RESULT` lines for same claim

**Cause**: Non-deterministic entity extraction (spaCy)

**Fix needed**: Make query formulation deterministic

#### Pattern B: Provider Timeouts
**Symptom**: Frequent `⏱️ TIMEOUT` messages

**Cause**: HTTP timeouts causing missed sources

**Fix needed**: Implement retry logic (Tier 2)

#### Pattern C: Provider Failover
**Symptom**: Brave fails → SerpAPI used inconsistently

**Cause**: Provider availability issues

**Fix needed**: Circuit breaker pattern (Tier 2)

#### Pattern D: Zero Sources
**Symptom**: `⚠️ NO EVIDENCE` warnings

**Cause**: All search attempts failed

**Fix needed**: Investigate provider configuration

## 🔎 Detailed Log Analysis

### Extract All Queries from Backend Logs
```bash
# Windows PowerShell:
Select-String "🔎 QUERY RESULT" backend_logs.txt

# Expected: Identical queries for same claim across runs
```

### Count Provider Timeouts
```bash
Select-String "⏱️.*TIMEOUT" backend_logs.txt | Measure-Object
```

### Check Provider Usage
```bash
Select-String "Trying provider" backend_logs.txt
```

## 📈 Interpreting Variance

| Variance | Status | Action |
|----------|--------|--------|
| ±0-5 points | ✅ EXCELLENT | Query expansion working! |
| ±6-10 points | ⚠️ ACCEPTABLE | Investigate minor issues |
| ±11-20 points | ❌ POOR | Major problems - needs Tier 2 |
| ±21+ points | 🚨 CRITICAL | Baseline behavior - urgent fix |

## 🛠️ Troubleshooting

### Test won't start
```
❌ Cannot connect to API at http://localhost:8000
```
**Fix**: Start backend first:
```bash
cd backend
uvicorn main:app --reload
```

### All runs fail
Check:
1. `.env` file has API keys (BRAVE_API_KEY, SERP_API_KEY)
2. Search providers are configured correctly
3. Internet connection is working

### Inconsistent results
**Expected!** That's what we're testing. Follow the analysis steps above to determine the root cause.

## 📝 Next Steps After Testing

### If Variance ≤ 5 points:
✅ Query expansion is working!
- Enable Phase 2: `ENABLE_PRIMARY_SOURCE_DETECTION=true`
- Continue Tier 1 rollout

### If Variance > 5 points:
❌ Further investigation needed:

1. **Analyze logs** for patterns (see above)
2. **Determine root cause**:
   - Query variance → Fix query formulation
   - Timeout issues → Implement Tier 2 (retry logic)
   - Provider issues → Implement circuit breakers

3. **Report findings** with:
   - Variance statistics
   - Log excerpts showing the problem
   - Pattern analysis

## 📞 Support

If you see unexpected patterns or need help interpreting results, provide:
1. `summary.json` from the test session
2. Relevant backend log excerpts (especially 🔎 and ❌ lines)
3. Description of what you expected vs. what you saw
