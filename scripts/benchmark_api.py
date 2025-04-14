#!/usr/bin/env python3
"""
Benchmark script for testing the MongoDB Atlas Search API performance.
Runs various load tests and performance benchmarks.
"""

import os
import sys
import json
import time
import asyncio
import random
import argparse
from typing import List, Dict, Any
import aiohttp
import statistics
from datetime import datetime

# Sample test data
SAMPLE_PRODUCT_QUERIES = [
    "baby",
    "shoes",
    "leke",
    "barnevogn",
    "rød",
    "blue",
    "kjøkken",
    "regntøy",
    "comfortable",
    "winter"
]

SAMPLE_PRODUCT_IDS = [
    "prod1",
    "prod2",
    "prod3",
    "prod4",
    "prod5"
]

SAMPLE_FILTERS = [
    {},
    {"ageBucket": "1 to 3 years"},
    {"color": "red"},
    {"isOnSale": True},
    {"brand": "BabySteps"},
    {"productType": "main", "isOnSale": True}
]

class APIBenchmark:
    """
    Benchmarks different aspects of the MongoDB Atlas Search API
    """
    
    def __init__(self, api_url: str, api_key: str):
        """
        Initialize benchmark with API details
        
        Args:
            api_url: Base URL for the API
            api_key: API key for authorization
        """
        self.api_url = api_url
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json",
            "x-apikey": api_key
        }
    
    async def check_health(self) -> bool:
        """Check if the API is healthy before benchmarking"""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{self.api_url}/health") as response:
                    if response.status == 200:
                        return True
                    return False
            except Exception as e:
                print(f"Error checking API health: {str(e)}")
                return False
    
    async def benchmark_search(self, 
                             concurrency: int = 10, 
                             total_requests: int = 100) -> Dict[str, Any]:
        """
        Benchmark search endpoint performance
        
        Args:
            concurrency: Number of concurrent requests
            total_requests: Total number of requests to send
            
        Returns:
            Dictionary with benchmark results
        """
        # Generate random search queries
        search_requests = []
        for _ in range(total_requests):
            search_requests.append({
                "query": random.choice(SAMPLE_PRODUCT_QUERIES),
                "filters": random.choice(SAMPLE_FILTERS),
                "limit": 10,
                "offset": 0
            })
        
        # Run benchmark
        results = await self._run_benchmark(
            f"{self.api_url}/search",
            search_requests,
            concurrency
        )
        
        return {
            "endpoint": "search",
            **results
        }
    
    async def benchmark_autosuggest(self, 
                                  concurrency: int = 10, 
                                  total_requests: int = 100) -> Dict[str, Any]:
        """
        Benchmark autosuggest endpoint performance
        
        Args:
            concurrency: Number of concurrent requests
            total_requests: Total number of requests to send
            
        Returns:
            Dictionary with benchmark results
        """
        # Generate random autosuggest queries
        autosuggest_requests = []
        for _ in range(total_requests):
            query = random.choice(SAMPLE_PRODUCT_QUERIES)
            prefix = query[:random.randint(1, len(query))]
            autosuggest_requests.append({
                "prefix": prefix,
                "limit": 5
            })
        
        # Run benchmark
        results = await self._run_benchmark(
            f"{self.api_url}/autosuggest",
            autosuggest_requests,
            concurrency
        )
        
        return {
            "endpoint": "autosuggest",
            **results
        }
    
    async def benchmark_recommendations(self, 
                                      concurrency: int = 5, 
                                      total_requests: int = 50) -> Dict[str, Any]:
        """
        Benchmark recommendations endpoint performance
        
        Args:
            concurrency: Number of concurrent requests
            total_requests: Total number of requests to send
            
        Returns:
            Dictionary with benchmark results
        """
        # Generate random recommendation requests
        recommendation_requests = []
        algorithms = ["hybrid", "co_occurrence", "embedding"]
        
        for _ in range(total_requests):
            recommendation_requests.append({
                "productId": random.choice(SAMPLE_PRODUCT_IDS),
                "limit": 5,
                "algorithm": random.choice(algorithms)
            })
        
        # Run benchmark
        results = await self._run_benchmark(
            endpoint=None,  # Special case handled in _run_benchmark
            payloads=recommendation_requests,
            concurrency=concurrency,
            is_recommendation=True
        )
        
        return {
            "endpoint": "recommendations",
            **results
        }
    
    async def _run_benchmark(self, 
                           endpoint: str, 
                           payloads: List[Dict[str, Any]], 
                           concurrency: int,
                           is_recommendation: bool = False) -> Dict[str, Any]:
        """
        Run benchmark for a specific endpoint
        
        Args:
            endpoint: API endpoint URL
            payloads: List of request payloads
            concurrency: Maximum concurrent requests
            is_recommendation: Whether this is a recommendation endpoint
            
        Returns:
            Dictionary with benchmark results
        """
        start_time = time.time()
        semaphore = asyncio.Semaphore(concurrency)
        results = []
        
        async def worker(payload):
            async with semaphore:
                start = time.time()
                try:
                    async with aiohttp.ClientSession() as session:
                        if is_recommendation:
                            # Special case for recommendations
                            product_id = payload["productId"]
                            url = f"{self.api_url}/similar/{product_id}"
                            # Remove productId from payload as it's in the URL
                            request_payload = {k: v for k, v in payload.items() if k != "productId"}
                        else:
                            url = endpoint
                            request_payload = payload
                            
                        async with session.post(
                            url, 
                            headers=self.headers, 
                            json=request_payload
                        ) as response:
                            status_code = response.status
                            if status_code == 200:
                                success = True
                                try:
                                    response_data = await response.json()
                                except:
                                    response_data = await response.text()
                            else:
                                success = False
                                response_data = await response.text()
                except Exception as e:
                    success = False
                    status_code = 0
                    response_data = str(e)
                
                duration_ms = (time.time() - start) * 1000
                return {
                    "success": success,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                    "response_size": len(str(response_data)) if success else 0
                }
        
        # Run all tasks
        tasks = [worker(payload) for payload in payloads]
        results = await asyncio.gather(*tasks)
        
        # Calculate statistics
        total_duration_ms = (time.time() - start_time) * 1000
        durations = [r["duration_ms"] for r in results]
        success_count = sum(1 for r in results if r["success"])
        
        # Sort durations for percentile calculation
        sorted_durations = sorted(durations)
        p50_index = int(len(sorted_durations) * 0.5)
        p95_index = int(len(sorted_durations) * 0.95)
        p99_index = int(len(sorted_durations) * 0.99)
        
        return {
            "total_requests": len(results),
            "successful_requests": success_count,
            "failed_requests": len(results) - success_count,
            "success_rate": success_count / len(results) if results else 0,
            "total_duration_ms": total_duration_ms,
            "throughput_rps": len(results) / (total_duration_ms / 1000) if total_duration_ms > 0 else 0,
            "avg_request_ms": statistics.mean(durations) if durations else 0,
            "min_request_ms": min(durations) if durations else 0,
            "max_request_ms": max(durations) if durations else 0,
            "p50_request_ms": sorted_durations[p50_index] if durations else 0,
            "p95_request_ms": sorted_durations[p95_index] if durations else 0,
            "p99_request_ms": sorted_durations[p99_index] if durations else 0,
            "concurrency": concurrency,
            "timestamp": datetime.now().isoformat()
        }
    
    async def run_full_benchmark(self, 
                              search_concurrency: int = 10, 
                              search_requests: int = 100,
                              autosuggest_concurrency: int = 20, 
                              autosuggest_requests: int = 200,
                              recommendation_concurrency: int = 5, 
                              recommendation_requests: int = 50) -> Dict[str, Any]:
        """
        Run full benchmark suite on all endpoints
        
        Args:
            search_concurrency: Concurrency for search endpoint
            search_requests: Total requests for search endpoint
            autosuggest_concurrency: Concurrency for autosuggest endpoint
            autosuggest_requests: Total requests for autosuggest endpoint
            recommendation_concurrency: Concurrency for recommendation endpoint
            recommendation_requests: Total requests for recommendation endpoint
            
        Returns:
            Dictionary with all benchmark results
        """
        # Check API health first
        is_healthy = await self.check_health()
        if not is_healthy:
            return {"error": "API is not healthy. Please check the API status."}
        
        # Run all benchmarks
        search_results = await self.benchmark_search(search_concurrency, search_requests)
        autosuggest_results = await self.benchmark_autosuggest(autosuggest_concurrency, autosuggest_requests)
        recommendation_results = await self.benchmark_recommendations(recommendation_concurrency, recommendation_requests)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "api_url": self.api_url,
            "search": search_results,
            "autosuggest": autosuggest_results,
            "recommendations": recommendation_results,
            "overall_throughput": (
                search_results["throughput_rps"] +
                autosuggest_results["throughput_rps"] +
                recommendation_results["throughput_rps"]
            ),
            "overall_p95_ms": max([
                search_results["p95_request_ms"],
                autosuggest_results["p95_request_ms"],
                recommendation_results["p95_request_ms"]
            ])
        }

async def main():
    parser = argparse.ArgumentParser(description="Benchmark MongoDB Atlas Search API")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--api-key", default="dev_api_key_12345", help="API key")
    parser.add_argument("--output", help="Output file for benchmark results (JSON)")
    parser.add_argument("--search-concurrency", type=int, default=10, help="Concurrency for search requests")
    parser.add_argument("--search-requests", type=int, default=100, help="Number of search requests")
    parser.add_argument("--autosuggest-concurrency", type=int, default=20, help="Concurrency for autosuggest requests")
    parser.add_argument("--autosuggest-requests", type=int, default=200, help="Number of autosuggest requests")
    parser.add_argument("--recommendation-concurrency", type=int, default=5, help="Concurrency for recommendation requests")
    parser.add_argument("--recommendation-requests", type=int, default=50, help="Number of recommendation requests")
    
    args = parser.parse_args()
    
    # Create benchmark instance
    benchmark = APIBenchmark(args.api_url, args.api_key)
    
    print(f"Starting benchmarks against {args.api_url}")
    print("This may take a few minutes depending on the concurrency and request count...")
    
    # Run full benchmark
    results = await benchmark.run_full_benchmark(
        search_concurrency=args.search_concurrency,
        search_requests=args.search_requests,
        autosuggest_concurrency=args.autosuggest_concurrency,
        autosuggest_requests=args.autosuggest_requests,
        recommendation_concurrency=args.recommendation_concurrency,
        recommendation_requests=args.recommendation_requests
    )
    
    # Output results
    print("\n===== BENCHMARK RESULTS =====")
    print(f"API URL: {args.api_url}")
    print(f"Timestamp: {results.get('timestamp')}")
    print("\n--- SEARCH ---")
    search_results = results.get("search", {})
    print(f"Requests: {search_results.get('total_requests')}")
    print(f"Success Rate: {search_results.get('success_rate', 0):.2%}")
    print(f"Throughput: {search_results.get('throughput_rps', 0):.2f} req/sec")
    print(f"Average Response Time: {search_results.get('avg_request_ms', 0):.2f} ms")
    print(f"P95 Response Time: {search_results.get('p95_request_ms', 0):.2f} ms")
    
    print("\n--- AUTOSUGGEST ---")
    autosuggest_results = results.get("autosuggest", {})
    print(f"Requests: {autosuggest_results.get('total_requests')}")
    print(f"Success Rate: {autosuggest_results.get('success_rate', 0):.2%}")
    print(f"Throughput: {autosuggest_results.get('throughput_rps', 0):.2f} req/sec")
    print(f"Average Response Time: {autosuggest_results.get('avg_request_ms', 0):.2f} ms")
    print(f"P95 Response Time: {autosuggest_results.get('p95_request_ms', 0):.2f} ms")
    
    print("\n--- RECOMMENDATIONS ---")
    recommendation_results = results.get("recommendations", {})
    print(f"Requests: {recommendation_results.get('total_requests')}")
    print(f"Success Rate: {recommendation_results.get('success_rate', 0):.2%}")
    print(f"Throughput: {recommendation_results.get('throughput_rps', 0):.2f} req/sec")
    print(f"Average Response Time: {recommendation_results.get('avg_request_ms', 0):.2f} ms")
    print(f"P95 Response Time: {recommendation_results.get('p95_request_ms', 0):.2f} ms")
    
    print("\n--- OVERALL ---")
    print(f"Total Throughput: {results.get('overall_throughput', 0):.2f} req/sec")
    print(f"Overall P95 Response Time: {results.get('overall_p95_ms', 0):.2f} ms")
    
    # Save results to file if specified
    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {args.output}")

if __name__ == "__main__":
    asyncio.run(main())
