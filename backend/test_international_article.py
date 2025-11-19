#!/usr/bin/env python3
"""
Test script for international article (Lula/Merz) after NLI threshold changes
"""
import requests
import time
import json

API_BASE = "http://localhost:8000"

# The article that previously failed (50/100 score)
article_url = "https://www.politico.eu/article/brazil-luiz-lula-germany-friedrich-merz-belem-cop30-climate-summit/"

print("=" * 80)
print("TESTING NLI THRESHOLD CHANGES")
print("=" * 80)
print(f"\nArticle: {article_url}")
print("\nPrevious results (BEFORE changes):")
print("  - Score: 50/100")
print("  - Claim 1: 0 sources (insufficient_evidence)")
print("  - Claim 2: 2 sources (insufficient_evidence)")
print("  - Claim 3: 0 sources (insufficient_evidence)")
print("\nExpected improvements (AFTER changes):")
print("  - Relevance threshold: 0.75 -> 0.65 (allows paraphrases)")
print("  - NLI logic: Low contradiction -> treat as support")
print("\n" + "=" * 80)

# Submit fact-check request
print("\n[1/4] Submitting fact-check request...")
response = requests.post(
    f"{API_BASE}/api/v1/checks",
    json={
        "input_type": "url",
        "input_content": article_url,
        "user_id": "test-user-123"
    },
    headers={"Authorization": "Bearer test-token"}
)

if response.status_code != 200:
    print(f"❌ Request failed: {response.status_code}")
    print(response.text)
    exit(1)

check_data = response.json()
check_id = check_data["id"]
print(f"✓ Check created: {check_id}")

# Poll for completion
print("\n[2/4] Waiting for pipeline to complete...")
max_wait = 120  # 2 minutes
start = time.time()
status = "pending"

while status not in ["completed", "failed"] and (time.time() - start) < max_wait:
    time.sleep(3)
    response = requests.get(
        f"{API_BASE}/api/v1/checks/{check_id}",
        headers={"Authorization": "Bearer test-token"}
    )

    if response.status_code == 200:
        check_data = response.json()
        status = check_data.get("status", "pending")
        print(f"  Status: {status}...")
    else:
        print(f"  Polling error: {response.status_code}")
        break

if status != "completed":
    print(f"\n❌ Check did not complete (status: {status})")
    exit(1)

print(f"✓ Pipeline completed in {int(time.time() - start)}s")

# Analyze results
print("\n[3/4] Analyzing results...")
print("\n" + "=" * 80)
print("RESULTS COMPARISON")
print("=" * 80)

claims = check_data.get("claims", [])
credibility_score = check_data.get("credibility_score", 0)

print(f"\nOverall Score: {credibility_score}/100")
print(f"Total Claims: {len(claims)}")

# Count verdicts
verdicts = {}
for claim in claims:
    verdict = claim.get("verdict", "unknown")
    verdicts[verdict] = verdicts.get(verdict, 0) + 1

print("\nVerdict Breakdown:")
for verdict, count in verdicts.items():
    print(f"  - {verdict}: {count} claims")

print("\n" + "-" * 80)
print("CLAIM DETAILS")
print("-" * 80)

for i, claim in enumerate(claims, 1):
    evidence_count = len(claim.get("evidence", []))
    verdict = claim.get("verdict", "unknown")
    confidence = claim.get("confidence", 0)

    print(f"\n[Claim {i}] {claim.get('text', 'N/A')[:80]}...")
    print(f"  Verdict: {verdict}")
    print(f"  Confidence: {confidence}%")
    print(f"  Evidence Sources: {evidence_count}")

    if evidence_count > 0:
        print("  Sources:")
        for ev in claim.get("evidence", [])[:3]:  # Show first 3
            source = ev.get("source", "Unknown")
            nli_stance = ev.get("nli_stance", "N/A")
            relevance = ev.get("relevance_score", 0)
            print(f"    - {source} (NLI: {nli_stance}, relevance: {relevance:.2f})")

# Success criteria
print("\n" + "=" * 80)
print("THRESHOLD CHANGE VALIDATION")
print("=" * 80)

success_count = 0
if credibility_score > 50:
    print("✓ Overall score improved (>50)")
    success_count += 1
else:
    print(f"✗ Overall score still low ({credibility_score}/100)")

supported_or_contradicted = sum(1 for c in claims if c.get("verdict") in ["supported", "contradicted"])
if supported_or_contradicted > 0:
    print(f"✓ {supported_or_contradicted} claims got definitive verdicts")
    success_count += 1
else:
    print("✗ No claims got definitive verdicts")

evidence_counts = [len(c.get("evidence", [])) for c in claims]
avg_evidence = sum(evidence_counts) / len(evidence_counts) if evidence_counts else 0
if avg_evidence >= 3:
    print(f"✓ Average evidence per claim: {avg_evidence:.1f} (≥3)")
    success_count += 1
else:
    print(f"✗ Average evidence per claim: {avg_evidence:.1f} (<3)")

print("\n" + "=" * 80)
if success_count >= 2:
    print("✓✓✓ THRESHOLD CHANGES WORKING - International content improved!")
else:
    print("⚠️  THRESHOLD CHANGES MAY NEED FURTHER ADJUSTMENT")
print("=" * 80)

# Save detailed results
with open("test_results_after_changes.json", "w") as f:
    json.dump(check_data, f, indent=2)
print("\n✓ Full results saved to: test_results_after_changes.json")
print(f"✓ Check ID for log analysis: {check_id}")
