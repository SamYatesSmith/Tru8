# Known Issues & Limitations

**Project**: Tru8 Pipeline Testing
**Last Updated**: 2025-11-03 14:40:00 UTC
**Code Version**: commit 388ac66
**Status**: Active Tracking

---

## 📊 Issue Summary

| Severity | Count | Resolved | Open |
|----------|-------|----------|------|
| 🔴 Critical | 0 | 0 | 0 |
| 🟡 High | 0 | 0 | 0 |
| 🟢 Medium | 0 | 0 | 0 |
| ⚪ Low | 0 | 0 | 0 |
| **TOTAL** | **0** | **0** | **0** |

---

## 🔴 CRITICAL ISSUES

*(Issues that block production deployment or cause data loss)*

### [TEMPLATE] Issue Title
**ID**: CRIT-001
**Reported**: YYYY-MM-DD
**Status**: 🔴 Open / 🟡 In Progress / 🟢 Resolved
**Affected Components**: Component names
**Severity**: Critical
**Impact**: Description of impact

**Description**:
Detailed description of the issue.

**Reproduction Steps**:
1. Step 1
2. Step 2
3. Step 3

**Expected Behavior**:
What should happen

**Actual Behavior**:
What actually happens

**Root Cause**:
Analysis of why this happens

**Workaround**:
Temporary solution if available

**Resolution**:
How this was/will be fixed

**Resolved By**: Name
**Resolved Date**: YYYY-MM-DD
**Regression Test**: `tests/regression/known_issues/test_issue_name.py`

---

## 🟡 HIGH PRIORITY ISSUES

*(Issues that significantly impact functionality or user experience)*

### [TEMPLATE] Issue Title
**ID**: HIGH-001
**Reported**: YYYY-MM-DD
**Status**: Status
**Affected Components**: Components
**Severity**: High

*(Same structure as critical issues)*

---

## 🟢 MEDIUM PRIORITY ISSUES

*(Issues that impact functionality but have workarounds)*

### [TEMPLATE] Issue Title
**ID**: MED-001
**Reported**: YYYY-MM-DD
**Status**: Status
**Affected Components**: Components
**Severity**: Medium

*(Same structure as critical issues)*

---

## ⚪ LOW PRIORITY ISSUES

*(Minor issues, cosmetic problems, or edge cases)*

### [TEMPLATE] Issue Title
**ID**: LOW-001
**Reported**: YYYY-MM-DD
**Status**: Status
**Affected Components**: Components
**Severity**: Low

*(Same structure as critical issues)*

---

## 🎯 RESOLVED ISSUES (Historical Reference)

### httpx Import Error - Backend Startup Failure
**ID**: HIST-001
**Reported**: 2025-11-03
**Resolved**: 2025-11-03
**Severity**: Critical
**Affected Components**: `backend/app/pipeline/ingest.py`

**Description**:
Backend failed to start due to missing `httpx` import. The `_check_robots_txt()` method used `httpx.AsyncClient` type hint but the module was never imported.

**Error Message**:
```
NameError: name 'httpx' is not defined
File "backend/app/pipeline/ingest.py", line 91
```

**Root Cause**:
Robots.txt checking feature added with httpx dependency but import statement was not included.

**Resolution**:
Commit 388ac66 removed the robots.txt checker entirely and switched to `requests` library. Feature was incorrectly blocking legitimate requests and robots.txt is advisory (not legally binding) for fact-checking purposes.

**Resolved By**: Commit 388ac66
**Resolved Date**: 2025-11-03
**Regression Test**: `tests/regression/known_issues/test_httpx_import_bug.py` (to be created in Phase 5)

**Lessons Learned**:
- Always import modules used in type hints
- Consider if features add value vs complexity
- Test backend startup in CI/CD

---

### Neutral Evidence Counted as Weak Support
**ID**: HIST-002
**Reported**: Prior to 2025-11-03
**Resolved**: Commit c6a79a1
**Severity**: High
**Affected Components**: `backend/app/pipeline/judge.py` - Consensus calculation

**Description**:
Neutral evidence (NLI stance = neutral) was being counted as weak support (40% weight towards supporting the claim), artificially inflating verdict confidence and skewing results towards "Supported."

**Root Cause**:
Consensus calculation logic incorrectly weighted neutral evidence as weak support instead of excluding it or giving it zero weight.

**Resolution**:
Commit c6a79a1 fixed the consensus calculation to handle neutral evidence appropriately. Now neutral evidence provides minimal signal (or is excluded) from consensus strength calculation.

**Resolved By**: Commit c6a79a1
**Resolved Date**: Prior to 2025-11-03
**Regression Test**: `tests/regression/known_issues/test_neutral_evidence_bug.py` (to be created in Phase 5)

---

## 📋 LIMITATIONS

*(Known limitations that are by design or accepted trade-offs)*

### Content Size Limits

**Limitation**: Image size limited to 6MB, video duration to 8 minutes (Quick mode)

**Reason**: Cost optimization and processing time constraints for MVP. Larger content would exceed latency targets (<10s) and increase token costs.

**Impact**: Users cannot fact-check large images or long videos in Quick mode.

**Future Enhancement**: Deep mode will support larger content with longer processing times.

**Documented In**: `LIMITS_AND_BOUNDARIES.md` (to be created in Phase 4)

---

### Robots.txt Compliance Disabled

**Limitation**: Pipeline does not respect robots.txt directives

**Reason**: Robots.txt was incorrectly blocking legitimate news sources. Fact-checking qualifies as fair use for publicly accessible content. Robots.txt is advisory, not legally binding.

**Impact**: May access sites that disallow bots (but only public content, respects HTTP 402 paywalls).

**Mitigation**: User-Agent identifies as "Tru8Bot/1.0 (Fact-checking service)" for transparency. Respects paywalls and copyright.

**Documented In**: Code comments in `ingest.py:52-54`

---

### English-Only Support (MVP)

**Limitation**: Pipeline optimized for English content only

**Reason**: MVP scope limitation. LLMs and NLI models trained primarily on English.

**Impact**: Non-English content may extract poorly or fail verification.

**Future Enhancement**: Multi-language support planned for post-MVP.

---

## 🔍 INVESTIGATION IN PROGRESS

*(Issues currently being investigated)*

### [TEMPLATE] Issue Under Investigation
**ID**: INV-001
**Reported**: YYYY-MM-DD
**Status**: 🔍 Investigating
**Assigned To**: Name
**Priority**: High/Med/Low

**Symptoms**:
What we're observing

**Investigation Notes**:
- Note 1
- Note 2

**Next Steps**:
- Action 1
- Action 2

---

## 📊 Issue Tracking Guidelines

### How to Report an Issue

1. **Identify severity**: Critical/High/Medium/Low
2. **Collect information**: Steps to reproduce, error logs, screenshots
3. **Add to this document**: Use template above
4. **Create regression test**: Once resolved, add test to prevent recurrence
5. **Update master tracker**: Link issue in relevant phase

### Severity Definitions

- **🔴 Critical**: System unusable, data loss, security vulnerability
- **🟡 High**: Major functionality broken, affects many users
- **🟢 Medium**: Functionality impaired, workaround exists
- **⚪ Low**: Minor issue, cosmetic, rare edge case

### Issue Lifecycle

1. **Reported** → Issue added to this document
2. **Triaged** → Severity assigned, priority set
3. **In Progress** → Investigation or fix underway
4. **Resolved** → Fix deployed and verified
5. **Tested** → Regression test created
6. **Closed** → Moved to "Resolved Issues" section

---

## 🔗 Related Documentation

- [TESTING_MASTER_TRACKER.md](./TESTING_MASTER_TRACKER.md) - Overall testing progress
- [LIMITS_AND_BOUNDARIES.md](./LIMITS_AND_BOUNDARIES.md) - System limits (Phase 4)
- [Phase Completion Reports](.) - Detailed phase findings
- [ERROR.md](../../../ERROR.md) - Original error log (archived)

---

**Document Version**: 1.0.0
**Maintained By**: Testing Team
**Review Frequency**: Weekly during testing phases, Monthly post-launch
