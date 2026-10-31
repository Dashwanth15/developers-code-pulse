"""Developers Code Pulse (DCP) — Production Performance and Latency Benchmark Script.

Executes concurrent HTTP requests against core API endpoints to measure:
- p50, p90, p95, p99 latencies
- Requests per second (RPS)
- Error rate and status distribution
"""

import asyncio
import time
from typing import Any

import httpx

TARGET_BASE_URL = "http://localhost:8000"
CONCURRENT_REQUESTS = 25
TOTAL_REQUESTS = 100


async def benchmark_endpoint(
    client: httpx.AsyncClient, method: str, endpoint: str, name: str
) -> dict[str, Any]:
    url = f"{TARGET_BASE_URL}{endpoint}"
    latencies: list[float] = []
    status_codes: dict[int, int] = {}

    start_bench = time.perf_counter()

    async def _single_request():
        req_start = time.perf_counter()
        try:
            res = await client.request(method, url, timeout=10.0)
            elapsed = time.perf_counter() - req_start
            latencies.append(elapsed)
            status_codes[res.status_code] = status_codes.get(res.status_code, 0) + 1
        except Exception as exc:
            elapsed = time.perf_counter() - req_start
            latencies.append(elapsed)
            status_codes[599] = status_codes.get(599, 0) + 1

    # Execute in concurrent batches
    tasks = [_single_request() for _ in range(TOTAL_REQUESTS)]
    await asyncio.gather(*tasks)

    total_time = time.perf_counter() - start_bench
    latencies.sort()

    def _quantile(p: float) -> float:
        if not latencies:
            return 0.0
        idx = int(len(latencies) * p)
        return latencies[min(idx, len(latencies) - 1)] * 1000.0  # in ms

    return {
        "endpoint": endpoint,
        "name": name,
        "total_requests": TOTAL_REQUESTS,
        "total_time_seconds": round(total_time, 2),
        "rps": round(TOTAL_REQUESTS / total_time, 1) if total_time > 0 else 0,
        "p50_ms": round(_quantile(0.50), 2),
        "p90_ms": round(_quantile(0.90), 2),
        "p95_ms": round(_quantile(0.95), 2),
        "p99_ms": round(_quantile(0.99), 2),
        "status_distribution": status_codes,
    }


async def run_all_benchmarks():
    print(f"Starting DCP API Benchmark against {TARGET_BASE_URL}...")
    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=CONCURRENT_REQUESTS)) as client:
        endpoints = [
            ("GET", "/api/v1/health", "Liveness Probe"),
            ("GET", "/api/v1/ready", "Readiness Probe (DB + Redis Pings)"),
            ("GET", "/", "Root Metadata Endpoint"),
            ("GET", "/metrics", "Prometheus Metrics Scraping"),
        ]

        results = []
        for method, ep, name in endpoints:
            print(f"Benchmarking {name} ({method} {ep})...")
            res = await benchmark_endpoint(client, method, ep, name)
            results.append(res)
            print(f"  -> RPS: {res['rps']} | p50: {res['p50_ms']}ms | p95: {res['p95_ms']}ms")

        print("\n=== BENCHMARK COMPLETE ===")
        return results


if __name__ == "__main__":
    asyncio.run(run_all_benchmarks())
