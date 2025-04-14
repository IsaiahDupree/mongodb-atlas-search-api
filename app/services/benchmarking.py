"""
Performance monitoring and benchmarking tools for MongoDB Atlas Search API.
Helps track, analyze, and optimize search and recommendation performance.
"""

import time
import statistics
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable, Awaitable
import concurrent.futures
from contextlib import contextmanager

class PerformanceTracker:
    """
    Tracks performance metrics for API operations.
    Maintains historical data for trend analysis.
    """
    
    # Store performance data
    _search_metrics: List[Dict[str, Any]] = []
    _recommendation_metrics: List[Dict[str, Any]] = []
    _endpoint_metrics: Dict[str, List[Dict[str, Any]]] = {}
    
    # Maximum number of metrics to store in memory
    _max_history = 1000
    
    @classmethod
    def track_search(cls, query: str, filters: Dict[str, Any], result_count: int, duration_ms: float) -> None:
        """
        Track search performance metrics.
        
        Args:
            query: Search query string
            filters: Search filters applied
            result_count: Number of results returned
            duration_ms: Query execution time in milliseconds
        """
        timestamp = datetime.now().isoformat()
        
        # Create metric record
        metric = {
            "timestamp": timestamp,
            "query": query,
            "filters": filters,
            "result_count": result_count,
            "duration_ms": duration_ms
        }
        
        # Add to history, maintain maximum size
        cls._search_metrics.append(metric)
        if len(cls._search_metrics) > cls._max_history:
            cls._search_metrics.pop(0)
    
    @classmethod
    def track_recommendation(cls, product_id: str, algorithm: str, result_count: int, duration_ms: float) -> None:
        """
        Track recommendation performance metrics.
        
        Args:
            product_id: Source product ID
            algorithm: Recommendation algorithm used
            result_count: Number of recommendations returned
            duration_ms: Execution time in milliseconds
        """
        timestamp = datetime.now().isoformat()
        
        # Create metric record
        metric = {
            "timestamp": timestamp,
            "product_id": product_id,
            "algorithm": algorithm,
            "result_count": result_count,
            "duration_ms": duration_ms
        }
        
        # Add to history, maintain maximum size
        cls._recommendation_metrics.append(metric)
        if len(cls._recommendation_metrics) > cls._max_history:
            cls._recommendation_metrics.pop(0)
    
    @classmethod
    def track_endpoint(cls, endpoint: str, status_code: int, duration_ms: float) -> None:
        """
        Track general endpoint performance metrics.
        
        Args:
            endpoint: API endpoint path
            status_code: HTTP status code
            duration_ms: Request processing time in milliseconds
        """
        timestamp = datetime.now().isoformat()
        
        # Create metric record
        metric = {
            "timestamp": timestamp,
            "status_code": status_code,
            "duration_ms": duration_ms
        }
        
        # Initialize endpoint entry if needed
        if endpoint not in cls._endpoint_metrics:
            cls._endpoint_metrics[endpoint] = []
        
        # Add to history, maintain maximum size
        cls._endpoint_metrics[endpoint].append(metric)
        if len(cls._endpoint_metrics[endpoint]) > cls._max_history:
            cls._endpoint_metrics[endpoint].pop(0)
    
    @classmethod
    def get_search_stats(cls, time_window_minutes: Optional[int] = None) -> Dict[str, Any]:
        """
        Get statistical summary of search performance.
        
        Args:
            time_window_minutes: Optional time window in minutes for filtering metrics
            
        Returns:
            Dictionary containing search performance statistics
        """
        # Filter metrics by time window if specified
        if time_window_minutes is not None:
            cutoff_time = datetime.now().timestamp() - (time_window_minutes * 60)
            metrics = [
                m for m in cls._search_metrics 
                if datetime.fromisoformat(m["timestamp"]).timestamp() >= cutoff_time
            ]
        else:
            metrics = cls._search_metrics
        
        # Return empty stats if no metrics
        if not metrics:
            return {
                "count": 0,
                "min_duration_ms": 0,
                "max_duration_ms": 0,
                "avg_duration_ms": 0,
                "p95_duration_ms": 0,
                "avg_results": 0
            }
        
        # Calculate statistics
        durations = [m["duration_ms"] for m in metrics]
        result_counts = [m["result_count"] for m in metrics]
        
        # Sort durations for percentile calculation
        sorted_durations = sorted(durations)
        p95_index = int(len(sorted_durations) * 0.95)
        
        return {
            "count": len(metrics),
            "min_duration_ms": min(durations),
            "max_duration_ms": max(durations),
            "avg_duration_ms": statistics.mean(durations) if durations else 0,
            "p95_duration_ms": sorted_durations[p95_index] if durations else 0,
            "avg_results": statistics.mean(result_counts) if result_counts else 0,
            "total_searches": len(cls._search_metrics)
        }
    
    @classmethod
    def get_recommendation_stats(cls, algorithm: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistical summary of recommendation performance.
        
        Args:
            algorithm: Optional filter by algorithm type
            
        Returns:
            Dictionary containing recommendation performance statistics
        """
        # Filter metrics by algorithm if specified
        if algorithm is not None:
            metrics = [m for m in cls._recommendation_metrics if m["algorithm"] == algorithm]
        else:
            metrics = cls._recommendation_metrics
        
        # Return empty stats if no metrics
        if not metrics:
            return {
                "count": 0,
                "min_duration_ms": 0,
                "max_duration_ms": 0,
                "avg_duration_ms": 0
            }
        
        # Calculate statistics
        durations = [m["duration_ms"] for m in metrics]
        
        return {
            "count": len(metrics),
            "min_duration_ms": min(durations),
            "max_duration_ms": max(durations),
            "avg_duration_ms": statistics.mean(durations) if durations else 0
        }
    
    @classmethod
    def get_endpoint_stats(cls) -> Dict[str, Dict[str, Any]]:
        """
        Get statistical summary of endpoint performance.
        
        Returns:
            Dictionary mapping endpoints to their performance statistics
        """
        result = {}
        
        for endpoint, metrics in cls._endpoint_metrics.items():
            if not metrics:
                continue
                
            # Calculate statistics
            durations = [m["duration_ms"] for m in metrics]
            success_rate = sum(1 for m in metrics if 200 <= m["status_code"] < 300) / len(metrics)
            
            result[endpoint] = {
                "count": len(metrics),
                "avg_duration_ms": statistics.mean(durations) if durations else 0,
                "max_duration_ms": max(durations),
                "success_rate": success_rate
            }
        
        return result

class Benchmark:
    """
    Benchmarking utilities for testing performance under various loads.
    """
    
    @staticmethod
    @contextmanager
    def timer():
        """
        Context manager for timing code execution.
        
        Yields:
            start_time: Start time in milliseconds
            
        Example:
            with Benchmark.timer() as t:
                # Code to time
                result = expensive_function()
                print(f"Time taken: {t.elapsed_ms} ms")
        """
        class Timer:
            def __init__(self):
                self.start = time.time()
                self.elapsed_ms = 0
                
            def update(self):
                self.elapsed_ms = (time.time() - self.start) * 1000
        
        timer = Timer()
        try:
            yield timer
        finally:
            timer.update()
    
    @staticmethod
    async def run_concurrent_load(
        func: Callable[..., Awaitable[Any]],
        args_list: List[Dict[str, Any]],
        concurrency: int = 10
    ) -> Dict[str, Any]:
        """
        Run a function with multiple sets of arguments concurrently.
        
        Args:
            func: Async function to benchmark
            args_list: List of argument dictionaries for each function call
            concurrency: Maximum number of concurrent executions
            
        Returns:
            Dictionary with benchmark results
        """
        semaphore = asyncio.Semaphore(concurrency)
        start_time = time.time()
        results = []
        
        async def worker(args):
            async with semaphore:
                start = time.time()
                try:
                    result = await func(**args)
                    success = True
                except Exception as e:
                    result = str(e)
                    success = False
                duration_ms = (time.time() - start) * 1000
                return {
                    "success": success,
                    "duration_ms": duration_ms,
                    "args": args,
                    "result": result if success else None,
                    "error": None if success else result
                }
        
        # Run all tasks
        tasks = [worker(args) for args in args_list]
        results = await asyncio.gather(*tasks)
        
        # Calculate statistics
        total_duration_ms = (time.time() - start_time) * 1000
        durations = [r["duration_ms"] for r in results]
        success_count = sum(1 for r in results if r["success"])
        
        return {
            "total_requests": len(results),
            "successful_requests": success_count,
            "failed_requests": len(results) - success_count,
            "success_rate": success_count / len(results) if results else 0,
            "total_duration_ms": total_duration_ms,
            "avg_request_ms": statistics.mean(durations) if durations else 0,
            "min_request_ms": min(durations) if durations else 0,
            "max_request_ms": max(durations) if durations else 0,
            "requests_per_second": len(results) / (total_duration_ms / 1000) if total_duration_ms > 0 else 0,
            "detailed_results": results
        }

# Export tracker instance
performance_tracker = PerformanceTracker()
