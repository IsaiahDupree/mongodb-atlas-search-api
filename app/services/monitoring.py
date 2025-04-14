import time
import logging
from typing import Dict, Any, Optional, List, Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class APIMonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware to monitor API requests and responses for performance tracking
    and error monitoring.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Start timer
        start_time = time.time()
        
        # Get request details
        method = request.method
        url = str(request.url)
        client_host = request.client.host if request.client else "unknown"
        
        # Process the request
        try:
            # Call the next middleware or route handler
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log successful request
            logger.info(
                f"Request: {method} {url} | Client: {client_host} | "
                f"Status: {response.status_code} | Time: {process_time:.4f}s"
            )
            
            # Add processing time header
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as e:
            # Calculate processing time for failed request
            process_time = time.time() - start_time
            
            # Log error
            logger.error(
                f"Request failed: {method} {url} | Client: {client_host} | "
                f"Error: {str(e)} | Time: {process_time:.4f}s"
            )
            
            # Re-raise the exception to be handled by FastAPI
            raise

class SearchMetrics:
    """
    Class to track and store search metrics for analysis
    """
    _queries: List[Dict[str, Any]] = []
    _max_stored_queries = 1000  # Limit storage to prevent memory issues
    
    @classmethod
    def record_search(cls, query: str, filters: Optional[Dict[str, Any]], 
                     results_count: int, processing_time: float) -> None:
        """Record a search query and its performance metrics"""
        search_record = {
            "timestamp": time.time(),
            "query": query,
            "filters": filters or {},
            "results_count": results_count,
            "processing_time": processing_time
        }
        
        # Add to list, maintaining max size
        cls._queries.append(search_record)
        if len(cls._queries) > cls._max_stored_queries:
            cls._queries.pop(0)  # Remove oldest
    
    @classmethod
    def get_recent_searches(cls, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent search queries"""
        return cls._queries[-limit:] if cls._queries else []
    
    @classmethod
    def get_average_processing_time(cls, last_n: int = 100) -> float:
        """Get average processing time for recent searches"""
        recent = cls._queries[-last_n:] if len(cls._queries) >= last_n else cls._queries
        if not recent:
            return 0.0
        
        total_time = sum(q["processing_time"] for q in recent)
        return total_time / len(recent)
    
    @classmethod
    def get_popular_queries(cls, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most popular search queries"""
        if not cls._queries:
            return []
        
        # Count query occurrences
        query_counts = {}
        for record in cls._queries:
            query = record["query"]
            query_counts[query] = query_counts.get(query, 0) + 1
        
        # Sort by count and return top N
        popular = sorted(query_counts.items(), key=lambda x: x[1], reverse=True)
        return [{"query": q, "count": c} for q, c in popular[:limit]]
