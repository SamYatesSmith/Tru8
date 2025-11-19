import requests
import time
import json

url = "https://www.politico.eu/article/brazil-luiz-lula-germany-friedrich-merz-belem-cop30-climate-summit/"

print("Submitting test...")
r = requests.post(
    "http://localhost:8000/api/v1/checks/test",
    json={"url": url}
)

if r.status_code != 201:
    print(f"Error {r.status_code}: {r.text}")
    exit(1)

data = r.json()
print(f"Response: {data}")
check_id = data.get("id") or data.get("check_id")
if not check_id:
    print("No check_id in response!")
    exit(1)
print(f"Check ID: {check_id}")
print("Waiting for completion...")

# Poll for completion
for i in range(40):  # 2 minutes max
    time.sleep(3)
    r = requests.get(f"http://localhost:8000/api/v1/checks/{check_id}")
    if r.status_code == 200:
        data = r.json()
        status = data.get("status")
        print(f"  {i*3}s: {status}")
        if status == "completed":
            break

if status != "completed":
    print(f"FAILED: {status}")
    exit(1)

print("\nRESULTS:")
print(f"Score: {data.get('credibility_score')}/100")
print(f"Claims: {len(data.get('claims', []))}")

for i, claim in enumerate(data.get("claims", []), 1):
    ev_count = len(claim.get("evidence", []))
    print(f"\nClaim {i}: {claim.get('text')[:60]}...")
    print(f"  Verdict: {claim.get('verdict')}")
    print(f"  Evidence: {ev_count} sources")

# Save results
with open("test_results_new.json", "w") as f:
    json.dump(data, f, indent=2)

print(f"\nFull results saved to test_results_new.json")
print(f"Check ID: {check_id}")
