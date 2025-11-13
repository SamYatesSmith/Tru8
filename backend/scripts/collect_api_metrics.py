"""
API Integration Metrics Collector
Week 5: Internal Rollout Monitoring

Collects and reports on Government API Integration metrics.
Run this script periodically (e.g., hourly) to track performance.

Usage:
    python scripts/collect_api_metrics.py
    python scripts/collect_api_metrics.py --output json
    python scripts/collect_api_metrics.py --alert --slack-webhook https://...
"""

import sys
import os
import json
import argparse
import requests
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy import create_engine, text
from tabulate import tabulate

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings


class APIMetricsCollector:
    """Collect and report API integration metrics."""

    def __init__(self, db_url: str = None, api_base_url: str = None):
        """
        Initialize metrics collector.

        Args:
            db_url: Database URL (defaults to settings.DATABASE_URL)
            api_base_url: API base URL (defaults to http://localhost:8000)
        """
        self.db_url = db_url or str(settings.DATABASE_URL)
        self.api_base_url = api_base_url or "http://localhost:8000"
        self.engine = create_engine(self.db_url)

    def collect_all_metrics(self) -> Dict[str, Any]:
        """
        Collect all metrics.

        Returns:
            Dictionary with all metrics
        """
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "database_metrics": self._collect_database_metrics(),
            "cache_metrics": self._collect_cache_metrics(),
            "circuit_breaker_metrics": self._collect_circuit_breaker_metrics(),
            "health_status": self._evaluate_health()
        }
        return metrics

    def _collect_database_metrics(self) -> Dict[str, Any]:
        """Collect metrics from database."""
        with self.engine.connect() as conn:
            # Summary metrics
            summary_query = text("""
                SELECT
                    COUNT(*) AS total_checks_24h,
                    COUNT(CASE WHEN api_call_count > 0 THEN 1 END) AS checks_with_api,
                    ROUND(
                        COUNT(CASE WHEN api_call_count > 0 THEN 1 END)::numeric /
                        NULLIF(COUNT(*), 0)::numeric * 100,
                        2
                    ) AS api_coverage_pct,
                    ROUND(AVG(processing_time_ms), 0) AS avg_latency_ms,
                    ROUND(percentile_cont(0.50) WITHIN GROUP (ORDER BY processing_time_ms), 0) AS p50_latency_ms,
                    ROUND(percentile_cont(0.95) WITHIN GROUP (ORDER BY processing_time_ms), 0) AS p95_latency_ms,
                    ROUND(percentile_cont(0.99) WITHIN GROUP (ORDER BY processing_time_ms), 0) AS p99_latency_ms,
                    ROUND(
                        COUNT(CASE WHEN status = 'failed' THEN 1 END)::numeric /
                        NULLIF(COUNT(*), 0)::numeric * 100,
                        2
                    ) AS error_rate_pct
                FROM "check"
                WHERE
                    status IN ('completed', 'failed')
                    AND created_at > NOW() - INTERVAL '24 hours'
            """)

            summary_result = conn.execute(summary_query).fetchone()

            # API sources used
            api_sources_query = text("""
                SELECT
                    api->>'name' AS api_name,
                    COUNT(*) AS times_used,
                    SUM((api->>'results')::int) AS total_results
                FROM "check",
                     jsonb_array_elements(api_sources_used::jsonb) AS api
                WHERE
                    created_at > NOW() - INTERVAL '24 hours'
                    AND api_sources_used IS NOT NULL
                GROUP BY api->>'name'
                ORDER BY times_used DESC
            """)

            api_sources = []
            for row in conn.execute(api_sources_query):
                api_sources.append({
                    "api_name": row[0],
                    "times_used": row[1],
                    "total_results": row[2]
                })

            return {
                "total_checks_24h": summary_result[0] or 0,
                "checks_with_api": summary_result[1] or 0,
                "api_coverage_percentage": float(summary_result[2] or 0),
                "avg_latency_ms": int(summary_result[3] or 0),
                "p50_latency_ms": int(summary_result[4] or 0),
                "p95_latency_ms": int(summary_result[5] or 0),
                "p99_latency_ms": int(summary_result[6] or 0),
                "error_rate_percentage": float(summary_result[7] or 0),
                "top_apis_used": api_sources[:5]
            }

    def _collect_cache_metrics(self) -> Dict[str, Any]:
        """Collect cache metrics from API endpoint."""
        try:
            response = requests.get(
                f"{self.api_base_url}/api/v1/health/cache-metrics",
                timeout=5
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def _collect_circuit_breaker_metrics(self) -> Dict[str, Any]:
        """Collect circuit breaker metrics from API endpoint."""
        try:
            response = requests.get(
                f"{self.api_base_url}/api/v1/health/circuit-breakers",
                timeout=5
            )
            response.raise_for_status()
            breakers = response.json()

            # Summary
            states = {"closed": 0, "open": 0, "half_open": 0}
            for breaker in breakers.values():
                state = breaker.get("state", "unknown")
                if state in states:
                    states[state] += 1

            return {
                "total_breakers": len(breakers),
                "states": states,
                "breakers": breakers
            }
        except Exception as e:
            return {"error": str(e)}

    def _evaluate_health(self) -> Dict[str, Any]:
        """Evaluate overall health based on metrics."""
        db_metrics = self._collect_database_metrics()

        checks = {
            "p95_latency": {
                "value": db_metrics.get("p95_latency_ms", 0),
                "target": 10000,
                "status": "pass" if db_metrics.get("p95_latency_ms", 0) < 10000 else "fail"
            },
            "api_coverage": {
                "value": db_metrics.get("api_coverage_percentage", 0),
                "target": "20-30%",
                "status": "pass" if 20 <= db_metrics.get("api_coverage_percentage", 0) <= 30 else "warning"
            },
            "error_rate": {
                "value": db_metrics.get("error_rate_percentage", 0),
                "target": "<1%",
                "status": "pass" if db_metrics.get("error_rate_percentage", 0) < 1 else "fail"
            }
        }

        # Overall status
        if any(check["status"] == "fail" for check in checks.values()):
            overall_status = "unhealthy"
        elif any(check["status"] == "warning" for check in checks.values()):
            overall_status = "degraded"
        else:
            overall_status = "healthy"

        return {
            "overall_status": overall_status,
            "checks": checks
        }

    def print_report(self, metrics: Dict[str, Any]):
        """Print human-readable report."""
        print("\n" + "="*80)
        print("API INTEGRATION METRICS REPORT")
        print(f"Generated: {metrics['timestamp']}")
        print("="*80 + "\n")

        # Database Metrics
        db = metrics["database_metrics"]
        print("📊 DATABASE METRICS (Last 24 Hours)")
        print("-" * 80)
        db_table = [
            ["Total Checks", db.get("total_checks_24h", 0)],
            ["Checks with API", db.get("checks_with_api", 0)],
            ["API Coverage", f"{db.get('api_coverage_percentage', 0):.2f}%"],
            ["Avg Latency", f"{db.get('avg_latency_ms', 0)}ms"],
            ["P50 Latency", f"{db.get('p50_latency_ms', 0)}ms"],
            ["P95 Latency", f"{db.get('p95_latency_ms', 0)}ms"],
            ["P99 Latency", f"{db.get('p99_latency_ms', 0)}ms"],
            ["Error Rate", f"{db.get('error_rate_percentage', 0):.2f}%"],
        ]
        print(tabulate(db_table, headers=["Metric", "Value"], tablefmt="simple"))

        # Top APIs
        if db.get("top_apis_used"):
            print("\n🔝 TOP APIs USED")
            print("-" * 80)
            api_table = [
                [api["api_name"], api["times_used"], api["total_results"]]
                for api in db["top_apis_used"]
            ]
            print(tabulate(api_table, headers=["API", "Times Used", "Total Results"], tablefmt="simple"))

        # Cache Metrics
        cache = metrics["cache_metrics"]
        if "error" not in cache:
            print("\n💾 CACHE METRICS")
            print("-" * 80)
            if "overall" in cache:
                overall = cache["overall"]
                cache_table = [
                    ["Total Queries", overall.get("total_queries", 0)],
                    ["Cache Hits", overall.get("total_hits", 0)],
                    ["Cache Misses", overall.get("total_misses", 0)],
                    ["Hit Rate", f"{overall.get('hit_rate_percentage', 0):.2f}%"],
                    ["Status", overall.get("status", "unknown")]
                ]
                print(tabulate(cache_table, headers=["Metric", "Value"], tablefmt="simple"))

        # Circuit Breakers
        cb = metrics["circuit_breaker_metrics"]
        if "error" not in cb:
            print("\n⚡ CIRCUIT BREAKERS")
            print("-" * 80)
            states = cb.get("states", {})
            cb_table = [
                ["Total Breakers", cb.get("total_breakers", 0)],
                ["Closed (✅)", states.get("closed", 0)],
                ["Open (🚨)", states.get("open", 0)],
                ["Half-Open (⚠️)", states.get("half_open", 0)]
            ]
            print(tabulate(cb_table, headers=["Status", "Count"], tablefmt="simple"))

            # Alert if any breakers open
            if states.get("open", 0) > 0:
                print("\n🚨 WARNING: Circuit breakers in OPEN state:")
                for name, breaker in cb.get("breakers", {}).items():
                    if breaker.get("state") == "open":
                        print(f"   - {name}: {breaker.get('failure_count', 0)} failures")

        # Health Status
        health = metrics["health_status"]
        print("\n🏥 HEALTH STATUS")
        print("-" * 80)

        status_emoji = {
            "healthy": "✅",
            "degraded": "⚠️",
            "unhealthy": "🚨"
        }

        overall = health["overall_status"]
        print(f"Overall: {status_emoji.get(overall, '❓')} {overall.upper()}\n")

        health_table = []
        for check_name, check in health["checks"].items():
            status_icon = {
                "pass": "✅",
                "warning": "⚠️",
                "fail": "🚨"
            }.get(check["status"], "❓")

            health_table.append([
                check_name,
                f"{check['value']} (target: {check['target']})",
                f"{status_icon} {check['status'].upper()}"
            ])

        print(tabulate(health_table, headers=["Check", "Value", "Status"], tablefmt="simple"))

        print("\n" + "="*80 + "\n")

    def send_slack_alert(self, metrics: Dict[str, Any], webhook_url: str):
        """Send alert to Slack if health checks fail."""
        health = metrics["health_status"]

        if health["overall_status"] == "healthy":
            return  # No alert needed

        # Build alert message
        color = "warning" if health["overall_status"] == "degraded" else "danger"
        emoji = "⚠️" if health["overall_status"] == "degraded" else "🚨"

        failed_checks = [
            f"• {name}: {check['value']} (target: {check['target']})"
            for name, check in health["checks"].items()
            if check["status"] != "pass"
        ]

        message = {
            "attachments": [{
                "color": color,
                "title": f"{emoji} API Integration Health Alert",
                "text": f"Status: *{health['overall_status'].upper()}*",
                "fields": [
                    {
                        "title": "Failed Checks",
                        "value": "\n".join(failed_checks),
                        "short": False
                    },
                    {
                        "title": "Timestamp",
                        "value": metrics["timestamp"],
                        "short": True
                    }
                ],
                "footer": "API Metrics Collector"
            }]
        }

        try:
            response = requests.post(webhook_url, json=message, timeout=5)
            response.raise_for_status()
            print(f"✅ Slack alert sent to {webhook_url}")
        except Exception as e:
            print(f"❌ Failed to send Slack alert: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Collect API integration metrics")
    parser.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)"
    )
    parser.add_argument(
        "--alert",
        action="store_true",
        help="Send Slack alert if health checks fail"
    )
    parser.add_argument(
        "--slack-webhook",
        type=str,
        help="Slack webhook URL for alerts"
    )
    parser.add_argument(
        "--db-url",
        type=str,
        help="Database URL (defaults to settings.DATABASE_URL)"
    )
    parser.add_argument(
        "--api-url",
        type=str,
        help="API base URL (defaults to http://localhost:8000)"
    )

    args = parser.parse_args()

    # Initialize collector
    collector = APIMetricsCollector(
        db_url=args.db_url,
        api_base_url=args.api_url
    )

    # Collect metrics
    print("Collecting metrics...", file=sys.stderr)
    metrics = collector.collect_all_metrics()

    # Output
    if args.output == "json":
        print(json.dumps(metrics, indent=2))
    else:
        collector.print_report(metrics)

    # Send alert if requested
    if args.alert and args.slack_webhook:
        if metrics["health_status"]["overall_status"] != "healthy":
            collector.send_slack_alert(metrics, args.slack_webhook)

    # Exit with appropriate code
    health_status = metrics["health_status"]["overall_status"]
    if health_status == "unhealthy":
        sys.exit(2)  # Critical
    elif health_status == "degraded":
        sys.exit(1)  # Warning
    else:
        sys.exit(0)  # Healthy


if __name__ == "__main__":
    main()
