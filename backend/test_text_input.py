import requests
import time
import json

# Article text from previous successful test
article_text = """BERLIN — Brazilian President Luiz Inácio Lula da Silva lashed out at Friedrich Merz after Germany's chancellor made remarks disparaging the South American country following his visit to the COP30 climate talks in Belém.

Speaking at an event in Berlin last week, Merz called the city a "shabby" place to hold a climate conference, questioning the choice of venue.

"I cannot recommend that someone go to Belém. There's nothing there," Merz said, according to Brazilian media reports.

The comments provoked a sharp response from Lula, who on Monday defended the host city, located in the Amazon region of Pará state.

"Merz should have gone to a pub and had a beer rather than visiting Belém," Lula said. "He should have tasted Pará's cuisine. Because he would have realized that Berlin doesn't offer him 10 percent of the quality that the state of Pará offers."
"""

print("=" * 60)
print("Testing NLI Threshold Changes with Text Input")
print("=" * 60)
print("Previous score: 50/100")
print("After changes: Relevance 0.75 -> 0.65")
print("             : Low contradiction -> weak support")
print("=" * 60)

r = requests.post(
    "http://localhost:8000/api/v1/checks/test",
    json={"url": "", "text": article_text}  # Use text input instead
)

if r.status_code != 201:
    print(f"Error {r.status_code}: {r.text}")
    exit(1)

data = r.json()
check_id = data.get("check_id")
print(f"\nCheck ID: {check_id}")
print("Waiting for completion (max 2 min)...")

# Poll for completion
status = None
for i in range(40):
    time.sleep(3)
    r = requests.get(f"http://localhost:8000/api/v1/checks/{check_id}")
    if r.status_code == 200:
        data = r.json()
        status = data.get("status")
        if i % 3 == 0:  # Print every 9s
            print(f"  {i*3}s: {status}")
        if status in ["completed", "failed"]:
            break

if status != "completed":
    print(f"\nFAILED: Status = {status}")
    if data.get("error_message"):
        print(f"Error: {data.get('error_message')}")
    exit(1)

# Analyze results
print("\n" + "=" * 60)
print("RESULTS")
print("=" * 60)
score = data.get('credibility_score', 0)
claims = data.get('claims', [])

print(f"\nOverall Score: {score}/100 (was 50/100)")
print(f"Claims: {len(claims)}")

verdicts = {}
for c in claims:
    v = c.get('verdict', 'unknown')
    verdicts[v] = verdicts.get(v, 0) + 1

print("\nVerdicts:")
for v, count in sorted(verdicts.items()):
    print(f"  {v}: {count}")

print("\n" + "-" * 60)
for i, claim in enumerate(claims, 1):
    ev_count = len(claim.get("evidence", []))
    text = claim.get("text", "")
    print(f"\n[{i}] {text[:70]}...")
    print(f"    Verdict: {claim.get('verdict')}")
    print(f"    Evidence: {ev_count} sources (was 0-2)")
    print(f"    Confidence: {claim.get('confidence')}%")

# Check improvement
print("\n" + "=" * 60)
print("ASSESSMENT")
print("=" * 60)

improvements = []
if score > 50:
    improvements.append(f"Score improved: {score}/100 > 50")
else:
    print(f"Score unchanged: {score}/100")

evidence_counts = [len(c.get("evidence", [])) for c in claims]
avg_ev = sum(evidence_counts) / len(evidence_counts) if evidence_counts else 0
if avg_ev >= 2.5:
    improvements.append(f"More evidence: avg {avg_ev:.1f} (was ~0.7)")
else:
    print(f"Evidence still low: avg {avg_ev:.1f}")

definitive = sum(1 for c in claims if c.get('verdict') in ['supported', 'contradicted'])
if definitive > 0:
    improvements.append(f"Definitive verdicts: {definitive}")
else:
    print("No definitive verdicts")

if improvements:
    print("\nImprovements detected:")
    for imp in improvements:
        print(f"  + {imp}")
    print("\nSUCCESS: Threshold changes are working!")
else:
    print("\nNeed further investigation")

print("\n" + "=" * 60)
print(f"Check ID: {check_id}")
print("=" * 60)

with open("test_results_new.json", "w") as f:
    json.dump(data, f, indent=2)
print("Results saved to test_results_new.json")
