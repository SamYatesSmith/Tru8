"""
Consistency Testing Script for Tru8 Fact-Checking Pipeline

Runs multiple fact-checks on the same URL and saves detailed logs for analysis.
This helps diagnose non-deterministic behavior in the pipeline.

Usage:
    python test_consistency.py --url "https://example.com/article" --runs 5 --wait 300
"""

import asyncio
import httpx
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import argparse
import sys

# API Configuration
API_BASE_URL = "http://localhost:8000"
API_ENDPOINT = "/api/v1/checks/test"  # Use test endpoint that bypasses auth


class ConsistencyTester:
    def __init__(self, url: str, num_runs: int = 5, wait_seconds: int = 300):
        self.url = url
        self.num_runs = num_runs
        self.wait_seconds = wait_seconds
        self.results: List[Dict] = []

        # Create logs directory
        self.logs_dir = Path("consistency_test_logs")
        self.logs_dir.mkdir(exist_ok=True)

        # Timestamp for this test session
        self.session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = self.logs_dir / self.session_timestamp
        self.session_dir.mkdir(exist_ok=True)

        print(f"[LOGS] Logs will be saved to: {self.session_dir}")

    async def run_single_check(self, run_number: int) -> Dict:
        """Run a single fact-check and capture results"""
        print(f"\n{'='*80}")
        print(f"[RUN {run_number}/{self.num_runs}] Starting at {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*80}")

        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                # Create check request
                response = await client.post(
                    f"{API_BASE_URL}{API_ENDPOINT}",
                    json={
                        "url": self.url,
                        "mode": "quick"
                    },
                    headers={
                        "Content-Type": "application/json"
                    }
                )

                response.raise_for_status()
                check_data = response.json()
                check_id = check_data.get("check_id")  # Test endpoint returns check_id directly

                print(f"[OK] Check created: {check_id}")

                # Poll for completion
                max_polls = 180  # 3 minutes max
                poll_interval = 2

                for poll in range(max_polls):
                    await asyncio.sleep(poll_interval)

                    # Use test GET endpoint: /api/v1/checks/test/{check_id}
                    status_response = await client.get(
                        f"{API_BASE_URL}/api/v1/checks/test/{check_id}"
                    )
                    status_response.raise_for_status()
                    status_data = status_response.json()

                    status = status_data.get("status")

                    if status == "completed":
                        elapsed = time.time() - start_time
                        print(f"[COMPLETE] Finished in {elapsed:.1f}s")

                        # Extract key metrics
                        overall_score = status_data.get("overall_score", 0)
                        claims_analyzed = status_data.get("claims_analyzed", 0)
                        supported = status_data.get("claims_supported", 0)
                        uncertain = status_data.get("claims_uncertain", 0)
                        contradicted = status_data.get("claims_contradicted", 0)

                        result = {
                            "run_number": run_number,
                            "check_id": check_id,
                            "timestamp": datetime.now().isoformat(),
                            "elapsed_seconds": round(elapsed, 1),
                            "overall_score": overall_score,
                            "claims_analyzed": claims_analyzed,
                            "claims_supported": supported,
                            "claims_uncertain": uncertain,
                            "claims_contradicted": contradicted,
                            "full_response": status_data
                        }

                        # Save detailed response to JSON
                        output_file = self.session_dir / f"run_{run_number:02d}_response.json"
                        with open(output_file, 'w', encoding='utf-8') as f:
                            json.dump(status_data, f, indent=2, ensure_ascii=False)

                        print(f"[SCORE] {overall_score}/100 | Claims: {claims_analyzed} | S:{supported} U:{uncertain} C:{contradicted}")
                        print(f"[SAVED] {output_file.name}")

                        return result

                    elif status == "failed":
                        error = status_data.get("error", "Unknown error")
                        print(f"[FAILED] {error}")
                        return {
                            "run_number": run_number,
                            "status": "failed",
                            "error": error,
                            "elapsed_seconds": time.time() - start_time
                        }

                    # Still processing
                    if poll % 10 == 0:  # Print every 20 seconds
                        print(f"[WAIT] Still processing... ({poll * poll_interval}s elapsed)")

                # Timeout
                print(f"[TIMEOUT] After {max_polls * poll_interval}s")
                return {
                    "run_number": run_number,
                    "status": "timeout",
                    "elapsed_seconds": time.time() - start_time
                }

        except httpx.HTTPError as e:
            print(f"[ERROR] HTTP: {e}")
            return {
                "run_number": run_number,
                "status": "http_error",
                "error": str(e),
                "elapsed_seconds": time.time() - start_time
            }
        except Exception as e:
            print(f"[ERROR] {e}")
            return {
                "run_number": run_number,
                "status": "error",
                "error": str(e),
                "elapsed_seconds": time.time() - start_time
            }

    async def run_all_checks(self):
        """Run all consistency checks"""
        print(f"\n[START] CONSISTENCY TEST STARTED")
        print(f"[URL] {self.url}")
        print(f"[RUNS] {self.num_runs}")
        print(f"[WAIT] Between runs: {self.wait_seconds}s ({self.wait_seconds/60:.1f} minutes)")
        print(f"[TIME] Total estimated: {(self.num_runs * self.wait_seconds + 600) / 60:.0f} minutes\n")

        for run in range(1, self.num_runs + 1):
            result = await self.run_single_check(run)
            self.results.append(result)

            # Wait before next run (except after last run)
            if run < self.num_runs:
                print(f"\n[PAUSE] Waiting {self.wait_seconds}s before next run...")
                for remaining in range(self.wait_seconds, 0, -30):
                    mins = remaining // 60
                    secs = remaining % 60
                    print(f"   [TIME] {mins:02d}:{secs:02d} remaining...", end='\r')
                    await asyncio.sleep(min(30, remaining))
                print()  # New line after countdown

    def analyze_results(self):
        """Analyze and print consistency metrics"""
        print(f"\n{'='*80}")
        print(f"[ANALYSIS] CONSISTENCY ANALYSIS")
        print(f"{'='*80}\n")

        # Filter successful runs
        successful_runs = [r for r in self.results if r.get("overall_score") is not None]

        if not successful_runs:
            print("[ERROR] No successful runs to analyze")
            return

        # Extract scores
        scores = [r["overall_score"] for r in successful_runs]
        claims_counts = [r["claims_analyzed"] for r in successful_runs]
        supported_counts = [r["claims_supported"] for r in successful_runs]

        # Calculate statistics
        min_score = min(scores)
        max_score = max(scores)
        avg_score = sum(scores) / len(scores)
        variance = max_score - min_score

        print(f"[SUCCESS] Successful runs: {len(successful_runs)}/{self.num_runs}")
        print(f"\n[SCORES] SCORE CONSISTENCY:")
        print(f"   Min:      {min_score}/100")
        print(f"   Max:      {max_score}/100")
        print(f"   Average:  {avg_score:.1f}/100")
        print(f"   Variance: ±{variance} points")

        if variance <= 5:
            print(f"   Status:   [EXCELLENT] (target: ±5 points)")
        elif variance <= 10:
            print(f"   Status:   [ACCEPTABLE] (target: ±5 points)")
        else:
            print(f"   Status:   [POOR] (target: ±5 points)")

        print(f"\n[CLAIMS] CLAIMS ANALYSIS:")
        print(f"   Claims analyzed:  {min(claims_counts)}-{max(claims_counts)} (variance: {max(claims_counts) - min(claims_counts)})")
        print(f"   Claims supported: {min(supported_counts)}-{max(supported_counts)} (variance: {max(supported_counts) - min(supported_counts)})")

        print(f"\n[TIME] PROCESSING TIME:")
        times = [r["elapsed_seconds"] for r in successful_runs]
        print(f"   Min:     {min(times):.1f}s")
        print(f"   Max:     {max(times):.1f}s")
        print(f"   Average: {sum(times)/len(times):.1f}s")

        # Save summary
        summary = {
            "test_session": self.session_timestamp,
            "url": self.url,
            "total_runs": self.num_runs,
            "successful_runs": len(successful_runs),
            "wait_seconds": self.wait_seconds,
            "statistics": {
                "score_min": min_score,
                "score_max": max_score,
                "score_avg": round(avg_score, 1),
                "score_variance": variance,
                "claims_analyzed_range": [min(claims_counts), max(claims_counts)],
                "claims_supported_range": [min(supported_counts), max(supported_counts)],
                "processing_time_avg": round(sum(times)/len(times), 1)
            },
            "runs": self.results
        }

        summary_file = self.session_dir / "summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        print(f"\n[SAVED] Summary saved to: {summary_file}")
        print(f"[LOGS] All logs in: {self.session_dir}")

        # Print recommendation
        print(f"\n{'='*80}")
        print(f"[NEXT] NEXT STEPS:")
        print(f"{'='*80}")

        if variance > 5:
            print("""
1. Check backend logs in the console where uvicorn is running
2. Look for patterns in diagnostic logs

3. Compare the query formulation between runs

4. Check if provider failover is occurring
            """)
        else:
            print("\n[SUCCESS] Consistency is EXCELLENT! Query expansion appears to be working.")


async def main():
    parser = argparse.ArgumentParser(description="Test Tru8 fact-checking consistency")
    parser.add_argument(
        "--url",
        type=str,
        default="https://rollcall.com/2025/10/24/east-wing-demolition-highlights-loopholes-in-preservation-law/",
        help="URL to fact-check (default: East Wing article)"
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=5,
        help="Number of test runs (default: 5)"
    )
    parser.add_argument(
        "--wait",
        type=int,
        default=60,  # 1 minute for faster testing, can increase to 300 (5 min)
        help="Seconds to wait between runs (default: 60)"
    )

    args = parser.parse_args()

    # Validate API is running
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{API_BASE_URL}/api/v1/health/")
            response.raise_for_status()
            print(f"[OK] API is running at {API_BASE_URL}\n")
    except Exception as e:
        print(f"[ERROR] Cannot connect to API at {API_BASE_URL}")
        print(f"   Error: {e}")
        print(f"\n[INFO] Make sure the backend is running:")
        print(f"   cd backend")
        print(f"   uvicorn main:app --reload")
        sys.exit(1)

    # Run tests
    tester = ConsistencyTester(
        url=args.url,
        num_runs=args.runs,
        wait_seconds=args.wait
    )

    try:
        await tester.run_all_checks()
        tester.analyze_results()
    except KeyboardInterrupt:
        print("\n\n[INTERRUPT] Test interrupted by user")
        if tester.results:
            print(f"[ANALYSIS] Analyzing {len(tester.results)} completed runs...")
            tester.analyze_results()
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
