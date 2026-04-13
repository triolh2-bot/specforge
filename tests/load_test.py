"""Load testing and performance validation for SpecForge.

Run with: locust -f tests/load_test.py --headless -u 50 -r 10 --run-time 60s --host http://localhost:5000

Or standalone without locust: python tests/load_test.py
"""

import json
import os
import statistics
import sys
import tempfile
import threading
import time
import urllib.request
import urllib.error
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _get_base_url():
    return os.environ.get("SPECFORGE_HOST", "http://localhost:5000")


# ---------------------------------------------------------------------------
# SLO definitions
# ---------------------------------------------------------------------------

SLOS = {
    "analyze_p50_ms": 500,       # 50% of analyses should complete in < 500ms
    "analyze_p95_ms": 2000,      # 95% should complete in < 2s
    "analyze_p99_ms": 5000,      # 99% should complete in < 5s
    "analyze_error_rate": 0.01,  # < 1% error rate
    "analyze_success_rate": 0.99, # > 99% success rate
    "health_p95_ms": 100,        # Health check < 100ms p95
    "throughput_min_rps": 5,     # Minimum 5 requests/second
}


# ---------------------------------------------------------------------------
# Simple load test runner (works without locust)
# ---------------------------------------------------------------------------

def _post_json(url, data):
    """Send a POST request with JSON body. Returns (status, duration_ms)."""
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp.read()
            duration = (time.perf_counter() - start) * 1000
            return resp.status, duration
    except urllib.error.HTTPError as e:
        duration = (time.perf_counter() - start) * 1000
        return e.code, duration
    except Exception:
        duration = (time.perf_counter() - start) * 1000
        return 0, duration


def _get(url):
    """Send a GET request. Returns (status, duration_ms)."""
    req = urllib.request.Request(url, method="GET")
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
            duration = (time.perf_counter() - start) * 1000
            return resp.status, duration
    except urllib.error.HTTPError as e:
        duration = (time.perf_counter() - start) * 1000
        return e.code, duration
    except Exception:
        duration = (time.perf_counter() - start) * 1000
        return 0, duration


def run_load_test(num_requests=50, concurrent=5):
    """Run a simple load test and return results."""
    base_url = _get_base_url()
    results = {"analyze": [], "health": [], "errors": 0, "total": 0}
    lock = threading.Lock()

    requirements_samples = [
        "Build an e-commerce store for my bakery with cart, checkout, and admin panel.",
        "Create a SaaS project management tool with team workspaces and subscription billing.",
        "I need a CRM for sales teams with lead tracking, pipeline management, and email integration.",
        "Build a mobile fitness app with workout logging, progress photos, and GPS tracking.",
        "Create a REST API with JWT auth, rate limiting, and OpenAPI documentation.",
    ]

    def worker():
        while True:
            with lock:
                if results["total"] >= num_requests:
                    return
                results["total"] += 1
                req_id = results["total"]

            sample = requirements_samples[(req_id - 1) % len(requirements_samples)]

            # Analyze request
            status, duration = _post_json(
                f"{base_url}/analyze",
                {"requirements": sample, "ai_enhance": False, "ai_provider": "openrouter"},
            )
            with lock:
                if 200 <= status < 300:
                    results["analyze"].append(duration)
                else:
                    results["errors"] += 1

            # Health check (every 5th request)
            if req_id % 5 == 0:
                h_status, h_duration = _get(f"{base_url}/health")
                with lock:
                    if 200 <= h_status < 300:
                        results["health"].append(h_duration)

    # Run workers
    threads = []
    for _ in range(concurrent):
        t = threading.Thread(target=worker)
        t.start()
        threads.append(t)

    for t in threads:
        t.join(timeout=120)

    return results


def percentile(data, p):
    """Calculate percentile."""
    if not data:
        return 0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * (p / 100)
    f = int(k)
    c = f + 1 if f + 1 < len(sorted_data) else f
    return sorted_data[f] + (k - f) * (sorted_data[c] - sorted_data[f]) if c != f else sorted_data[f]


def print_report(results):
    """Print a human-readable load test report."""
    analyze = results["analyze"]
    health = results["health"]
    total = results["total"]
    errors = results["errors"]

    print("\n" + "=" * 60)
    print("  SpecForge Load Test Report")
    print("=" * 60)

    print(f"\n  Total requests:  {total}")
    print(f"  Errors:          {errors} ({errors/total*100:.1f}%)" if total else "  Errors:          0")
    print(f"  Success rate:    {(total-errors)/total*100:.1f}%" if total else "  Success rate:    N/A")

    if analyze:
        print(f"\n  ── Analysis Endpoint ──")
        print(f"  Count:           {len(analyze)}")
        print(f"  Min:             {min(analyze):.0f}ms")
        print(f"  Max:             {max(analyze):.0f}ms")
        print(f"  Mean:            {statistics.mean(analyze):.0f}ms")
        print(f"  Median (p50):    {percentile(analyze, 50):.0f}ms")
        print(f"  p95:             {percentile(analyze, 95):.0f}ms")
        print(f"  p99:             {percentile(analyze, 99):.0f}ms")

        # SLO checks
        print(f"\n  ── SLO Validation ──")
        checks = [
            ("analyze_p50_ms", percentile(analyze, 50)),
            ("analyze_p95_ms", percentile(analyze, 95)),
            ("analyze_p99_ms", percentile(analyze, 99)),
        ]
        all_pass = True
        for slo_name, value in checks:
            target = SLOS[slo_name]
            passed = value <= target
            all_pass = all_pass and passed
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"  {status}  {slo_name}: {value:.0f}ms (target: ≤{target}ms)")

        error_rate = errors / total if total > 0 else 0
        passed = error_rate <= SLOS["analyze_error_rate"]
        all_pass = all_pass and passed
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}  error_rate: {error_rate:.2%} (target: ≤{SLOS['analyze_error_rate']:.0%})")

        print(f"\n  Overall: {'✓ ALL SLOS MET' if all_pass else '✗ SLOS VIOLATED'}")

    if health:
        print(f"\n  ── Health Endpoint ──")
        print(f"  Count:           {len(health)}")
        print(f"  p95:             {percentile(health, 95):.0f}ms")
        target = SLOS["health_p95_ms"]
        passed = percentile(health, 95) <= target
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}  health_p95_ms: {percentile(health, 95):.0f}ms (target: ≤{target}ms)")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    # Check if server is running
    base_url = _get_base_url()
    try:
        status, _ = _get(f"{base_url}/health")
        if status not in (200, 503):
            print(f"Server at {base_url} is not responding (status: {status})")
            print("Start the server first: flask run or docker-compose up")
            sys.exit(1)
    except Exception:
        print(f"Cannot reach server at {base_url}")
        print("Start the server first: flask run or docker-compose up")
        sys.exit(1)

    num = int(os.environ.get("LOAD_TEST_REQUESTS", "50"))
    conc = int(os.environ.get("LOAD_TEST_CONCURRENCY", "5"))

    print(f"Running load test: {num} requests, {conc} concurrent")
    results = run_load_test(num_requests=num, concurrent=conc)
    print_report(results)

    # Exit with non-zero if SLOs are violated
    analyze = results["analyze"]
    if analyze:
        if (percentile(analyze, 95) > SLOS["analyze_p95_ms"] or
                results["errors"] / results["total"] > SLOS["analyze_error_rate"]):
            sys.exit(1)
