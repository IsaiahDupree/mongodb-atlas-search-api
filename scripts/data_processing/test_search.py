#!/usr/bin/env python
"""
Search Testing Script

This script tests the search functionality of the MongoDB Atlas Search API
after data ingestion.

Usage:
    python test_search.py --api-url <api_url> --api-key <api_key> [--output <output_file>]
    python test_search.py --offline-mode --input <input_file> [--output <output_file>]

Arguments:
    --api-url       Base URL of the MongoDB Atlas Search API
    --api-key       API key for authentication
    --offline-mode  Run in offline mode without API connection
    --input         Path to transformed products JSON file (for offline mode)
    --output        Path to output file for search results (optional)
"""

import argparse
import json
import logging
import sys
import time
import random
from typing import Dict, List, Any, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("search_test")

# Constants
DEFAULT_TIMEOUT = 60  # seconds
MAX_RETRIES = 3
RETRY_BACKOFF = 0.5

# Sample test queries
TEST_QUERIES = [
    {
        "name": "Basic keyword search",
        "query": {
            "query": "aktivitetspakke",
            "limit": 10
        }
    },
    {
        "name": "Filtered search by price range",
        "query": {
            "query": "lego",
            "filters": {
                "priceRange": {
                    "min": 100,
                    "max": 500
                }
            },
            "limit": 10
        }
    },
    {
        "name": "Brand-specific search",
        "query": {
            "query": "kids concept",
            "limit": 10
        }
    },
    {
        "name": "Color filter search",
        "query": {
            "query": "furniture",
            "filters": {
                "color": "white"
            },
            "limit": 10
        }
    },
    {
        "name": "Book category search",
        "query": {
            "query": "bok book",
            "limit": 10
        }
    },
    {
        "name": "Seasonal product search",
        "query": {
            "query": "summer sommer",
            "limit": 10
        }
    },
    {
        "name": "Age-specific toy search",
        "query": {
            "query": "toy for babies",
            "limit": 10
        }
    },
    {
        "name": "Sale items search",
        "query": {
            "query": "discount sale",
            "filters": {
                "isOnSale": True
            },
            "limit": 10
        }
    }
]


def create_session() -> requests.Session:
    """
    Create a requests session with retry capabilities.
    
    Returns:
        Configured requests Session
    """
    session = requests.Session()
    
    # Configure retry strategy
    retry_strategy = Retry(
        total=MAX_RETRIES,
        backoff_factor=RETRY_BACKOFF,
        status_forcelist=[408, 429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session


def check_api_health(api_url: str, session: requests.Session) -> bool:
    """
    Check if the API is healthy.
    
    Args:
        api_url: Base URL of the API
        session: Requests session
        
    Returns:
        True if the API is healthy, False otherwise
    """
    try:
        health_url = f"{api_url.rstrip('/')}/health"
        response = session.get(health_url, timeout=DEFAULT_TIMEOUT)
        
        if response.status_code == 200:
            logger.info("API health check successful")
            return True
        else:
            logger.error(f"API health check failed: {response.status_code} {response.text}")
            return False
    
    except Exception as e:
        logger.error(f"API health check failed: {str(e)}")
        return False


def execute_search_query(api_url: str, api_key: str, query: Dict[str, Any], 
                        session: requests.Session) -> Dict[str, Any]:
    """
    Execute a search query.
    
    Args:
        api_url: Base URL of the API
        api_key: API key for authentication
        query: Search query parameters
        session: Requests session
        
    Returns:
        Search results
    """
    search_url = f"{api_url.rstrip('/')}/search"
    
    headers = {
        "Content-Type": "application/json",
        "x-apikey": api_key
    }
    
    try:
        response = session.post(
            search_url,
            headers=headers,
            json=query,
            timeout=DEFAULT_TIMEOUT
        )
        
        response.raise_for_status()
        return response.json()
    
    except requests.HTTPError as e:
        logger.error(f"HTTP error during search: {e}")
        
        # Try to get error details from response
        try:
            error_details = e.response.json()
            logger.error(f"Error details: {json.dumps(error_details, indent=2)}")
        except:
            logger.error(f"Response text: {e.response.text}")
        
        raise
    
    except Exception as e:
        logger.error(f"Error during search: {str(e)}")
        raise


def analyze_search_results(query_name: str, query: Dict[str, Any], 
                          results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze search results.
    
    Args:
        query_name: Name of the query
        query: Search query parameters
        results: Search results
        
    Returns:
        Analysis of the results
    """
    analysis = {
        "query_name": query_name,
        "query": query,
        "total_results": results.get("total", 0),
        "results_count": len(results.get("products", [])),
        "response_time_ms": None,  # Will be filled by caller
        "top_products": [],
        "has_facets": "facets" in results and results["facets"] is not None,
        "facet_count": len(results.get("facets", [])) if "facets" in results else 0,
        "query_explanation": "query_explanation" in results
    }
    
    # Add top 3 products
    for i, product in enumerate(results.get("products", [])[:3]):
        analysis["top_products"].append({
            "position": i + 1,
            "id": product.get("id", "unknown"),
            "title": product.get("title", "unknown"),
            "brand": product.get("brand", "unknown"),
            "price": product.get("priceCurrent", 0)
        })
    
    return analysis


def test_search(api_url: str, api_key: str, output_file: Optional[str] = None) -> None:
    """
    Test search functionality.
    
    Args:
        api_url: Base URL of the API
        api_key: API key for authentication
        output_file: Path to output file for search results (optional)
    """
    logger.info(f"Starting search tests against {api_url}")
    
    try:
        # Create a requests session
        session = create_session()
        
        # Check API health
        if not check_api_health(api_url, session):
            logger.error("API is not healthy, aborting search tests")
            return
        
        # Track test results
        test_results = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "api_url": api_url,
            "total_queries": len(TEST_QUERIES),
            "successful_queries": 0,
            "failed_queries": 0,
            "avg_response_time_ms": 0,
            "total_results": 0,
            "query_results": []
        }
        
        total_response_time = 0
        
        # Execute test queries
        for i, test in enumerate(TEST_QUERIES, 1):
            query_name = test["name"]
            query = test["query"]
            
            logger.info(f"Executing test query {i}/{len(TEST_QUERIES)}: {query_name}")
            
            try:
                start_time = time.time()
                results = execute_search_query(api_url, api_key, query, session)
                response_time = (time.time() - start_time) * 1000  # ms
                
                # Analyze results
                analysis = analyze_search_results(query_name, query, results)
                analysis["response_time_ms"] = response_time
                
                # Update test results
                test_results["successful_queries"] += 1
                test_results["total_results"] += analysis["total_results"]
                total_response_time += response_time
                test_results["query_results"].append(analysis)
                
                # Log results
                logger.info(f"Query: '{query.get('query', '')}' - Found {analysis['total_results']} results "
                           f"in {response_time:.2f} ms")
                
                if analysis["top_products"]:
                    logger.info(f"Top result: {analysis['top_products'][0].get('title', 'unknown')} "
                               f"({analysis['top_products'][0].get('brand', 'unknown')})")
                
                if analysis["has_facets"]:
                    logger.info(f"Search returned {analysis['facet_count']} facets")
                
            except Exception as e:
                logger.error(f"Error executing test query '{query_name}': {str(e)}")
                test_results["failed_queries"] += 1
                test_results["query_results"].append({
                    "query_name": query_name,
                    "query": query,
                    "error": str(e),
                    "status": "failed"
                })
            
            # Add a small delay between queries
            if i < len(TEST_QUERIES):
                time.sleep(0.5)
        
        # Calculate average response time
        if test_results["successful_queries"] > 0:
            test_results["avg_response_time_ms"] = total_response_time / test_results["successful_queries"]
        
        # Log final stats
        logger.info("Search tests complete")
        logger.info(f"Total queries: {test_results['total_queries']}")
        logger.info(f"Successful queries: {test_results['successful_queries']}")
        logger.info(f"Failed queries: {test_results['failed_queries']}")
        logger.info(f"Average response time: {test_results['avg_response_time_ms']:.2f} ms")
        logger.info(f"Total results found: {test_results['total_results']}")
        
        # Write results to file if requested
        if output_file:
            logger.info(f"Writing search test results to {output_file}")
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(test_results, f, indent=2, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"Error during search tests: {str(e)}")
        raise


def offline_search(input_file: str, output_file: Optional[str] = None) -> None:
    """
    Test search functionality in offline mode with local data.
    
    Args:
        input_file: Path to transformed products JSON file
        output_file: Path to output file for search results (optional)
    """
    try:
        logger.info(f"Starting offline search tests with data from {input_file}")
        
        # Load the products data
        with open(input_file, "r", encoding="utf-8") as f:
            products = json.load(f)
        
        logger.info(f"Loaded {len(products)} products for offline testing")
        
        # Initialize test results
        test_results = {
            "mode": "offline",
            "source_file": input_file,
            "total_queries": len(TEST_QUERIES),
            "successful_queries": 0,
            "failed_queries": 0,
            "total_products": len(products),
            "query_results": []
        }
        
        # Execute test queries
        for i, test in enumerate(TEST_QUERIES, 1):
            query_name = test["name"]
            query_params = test["query"]
            query_text = query_params.get("query", "")
            filters = query_params.get("filters", {})
            limit = query_params.get("limit", 10)
            
            logger.info(f"Executing offline test query {i}/{len(TEST_QUERIES)}: {query_name}")
            
            try:
                # Perform a simple word-matching search (this is a very simplified version)
                # In a real implementation, this would use more sophisticated search algorithms
                query_terms = query_text.lower().split()
                matching_products = []
                
                for product in products:
                    # Check if any query term is in the title or description
                    title = product.get("title", "").lower()
                    description = product.get("description", "").lower()
                    brand = product.get("brand", "").lower()
                    combined_text = f"{title} {description} {brand}"
                    
                    # Simple matching logic
                    matches = False
                    for term in query_terms:
                        if term in combined_text:
                            matches = True
                            break
                    
                    # Apply filters if any
                    if matches and filters:
                        # Price range filter
                        if "priceRange" in filters:
                            price_range = filters["priceRange"]
                            price = product.get("priceCurrent", 0)
                            min_price = price_range.get("min", 0)
                            max_price = price_range.get("max", float("inf"))
                            if not (min_price <= price <= max_price):
                                matches = False
                        
                        # Color filter
                        if "color" in filters and product.get("color") != filters["color"]:
                            matches = False
                        
                        # On sale filter
                        if "isOnSale" in filters and product.get("isOnSale", False) != filters["isOnSale"]:
                            matches = False
                    
                    if matches:
                        matching_products.append(product)
                
                # Sort results by relevance (in this simplified version, random)
                # In a real implementation, this would use more sophisticated ranking
                # For demo purposes, we'll shuffle to simulate different ranking results
                random.shuffle(matching_products)
                
                # Apply limit
                matching_products = matching_products[:limit]
                
                # Create a results object similar to what the API would return
                results = {
                    "products": matching_products,
                    "total": len(matching_products),
                    "facets": [],  # Simplified version doesn't support facets
                    "query": query_text
                }
                
                # Analyze results
                analysis = analyze_search_results(query_name, query_params, results)
                analysis["response_time_ms"] = 0  # No real API call
                
                # Update test results
                test_results["successful_queries"] += 1
                test_results["query_results"].append(analysis)
                
                # Log results
                logger.info(f"Query: '{query_text}' - Found {analysis['total_results']} results (offline mode)")
                
                if analysis["top_products"]:
                    logger.info(f"Top result: {analysis['top_products'][0].get('title', 'unknown')} ")
                
            except Exception as e:
                logger.error(f"Error executing offline test query '{query_name}': {str(e)}")
                test_results["failed_queries"] += 1
                test_results["query_results"].append({
                    "query_name": query_name,
                    "query": query_params,
                    "error": str(e),
                    "status": "failed"
                })
        
        # Log final stats
        logger.info("Offline search tests complete")
        logger.info(f"Total queries: {test_results['total_queries']}")
        logger.info(f"Successful queries: {test_results['successful_queries']}")
        logger.info(f"Failed queries: {test_results['failed_queries']}")
        
        # Write results to file if requested
        if output_file:
            logger.info(f"Writing offline search test results to {output_file}")
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(test_results, f, indent=2, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"Error during offline search tests: {str(e)}")
        raise


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Test search functionality of MongoDB Atlas Search API")
    
    # Create mutually exclusive group for mode selection
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--api-url", help="Base URL of the API (for online mode)")
    mode_group.add_argument("--offline-mode", action="store_true", help="Run in offline mode without API")
    
    # Other arguments
    parser.add_argument("--api-key", help="API key for authentication (for online mode)")
    parser.add_argument("--input", help="Path to transformed products JSON file (for offline mode)")
    parser.add_argument("--output", help="Path to output file for search results")
    
    args = parser.parse_args()
    
    # Validate argument combinations
    if args.api_url and not args.api_key:
        parser.error("--api-key is required when using --api-url")
    
    if args.offline_mode and not args.input:
        parser.error("--input is required when using --offline-mode")
    
    return args


if __name__ == "__main__":
    args = parse_args()
    
    if args.offline_mode:
        offline_search(args.input, args.output)
    else:
        test_search(args.api_url, args.api_key, args.output)
