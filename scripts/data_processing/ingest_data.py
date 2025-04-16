#!/usr/bin/env python
"""
Product Data Ingestion Script

This script ingests transformed product data into the MongoDB Atlas Search API.

Usage:
    python ingest_data.py --input <input_file> --api-url <api_url> --api-key <api_key> [--batch-size <batch_size>]

Arguments:
    --input       Path to the transformed JSON file
    --api-url     Base URL of the MongoDB Atlas Search API
    --api-key     API key for authentication
    --batch-size  Number of products to ingest per batch (default: 100)
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
logger = logging.getLogger("data_ingest")

# Constants
DEFAULT_BATCH_SIZE = 100
DEFAULT_TIMEOUT = 120  # seconds
MAX_RETRIES = 3
RETRY_BACKOFF = 0.5


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


def ingest_batch(api_url: str, api_key: str, batch: List[Dict[str, Any]], 
                session: requests.Session) -> Dict[str, Any]:
    """
    Ingest a batch of products.
    
    Args:
        api_url: Base URL of the API
        api_key: API key for authentication
        batch: List of products to ingest
        session: Requests session
        
    Returns:
        Response from the API
    """
    ingest_url = f"{api_url.rstrip('/')}/ingest/products"
    
    headers = {
        "Content-Type": "application/json",
        "x-apikey": api_key
    }
    
    try:
        response = session.post(
            ingest_url,
            headers=headers,
            json=batch,
            timeout=DEFAULT_TIMEOUT
        )
        
        response.raise_for_status()
        return response.json()
    
    except requests.HTTPError as e:
        logger.error(f"HTTP error during ingestion: {e}")
        
        # Try to get error details from response
        try:
            error_details = e.response.json()
            logger.error(f"Error details: {json.dumps(error_details, indent=2)}")
        except:
            logger.error(f"Response text: {e.response.text}")
        
        raise
    
    except Exception as e:
        logger.error(f"Error during ingestion: {str(e)}")
        raise


def verify_ingestion(api_url: str, api_key: str, product_ids: List[str], 
                    session: requests.Session) -> Dict[str, Any]:
    """
    Verify that products were ingested correctly.
    
    Args:
        api_url: Base URL of the API
        api_key: API key for authentication
        product_ids: List of product IDs to verify
        session: Requests session
        
    Returns:
        Verification results
    """
    # Sample a subset of products for verification
    sample_size = min(5, len(product_ids))
    sample_ids = random.sample(product_ids, sample_size)
    
    headers = {
        "x-apikey": api_key
    }
    
    results = {
        "checked": sample_size,
        "found": 0,
        "missing": 0,
        "missing_ids": []
    }
    
    for product_id in sample_ids:
        try:
            doc_url = f"{api_url.rstrip('/')}/doc/{product_id}"
            response = session.get(
                doc_url,
                headers=headers,
                timeout=DEFAULT_TIMEOUT
            )
            
            if response.status_code == 200:
                results["found"] += 1
            else:
                results["missing"] += 1
                results["missing_ids"].append(product_id)
        
        except Exception as e:
            logger.warning(f"Error verifying product {product_id}: {str(e)}")
            results["missing"] += 1
            results["missing_ids"].append(product_id)
    
    return results


def ingest_data(input_file: str, api_url: str, api_key: str, batch_size: int = DEFAULT_BATCH_SIZE) -> None:
    """
    Ingest product data into the API.
    
    Args:
        input_file: Path to the input JSON file
        api_url: Base URL of the API
        api_key: API key for authentication
        batch_size: Number of products to ingest per batch
    """
    logger.info(f"Starting data ingestion from {input_file} to {api_url}")
    
    try:
        # Read input file
        logger.info("Reading input file...")
        with open(input_file, "r", encoding="utf-8") as f:
            products = json.load(f)
        
        total_products = len(products)
        logger.info(f"Found {total_products} products to ingest")
        
        # Create a requests session
        session = create_session()
        
        # Check API health
        if not check_api_health(api_url, session):
            logger.error("API is not healthy, aborting ingestion")
            return
        
        # Split into batches
        batches = [products[i:i + batch_size] for i in range(0, len(products), batch_size)]
        logger.info(f"Split into {len(batches)} batches of up to {batch_size} products each")
        
        # Track ingestion stats
        ingestion_stats = {
            "total_products": total_products,
            "batches_sent": 0,
            "batches_successful": 0,
            "total_inserted": 0,
            "total_updated": 0,
            "total_errors": 0,
            "start_time": time.time()
        }
        
        # Ingest batches
        for i, batch in enumerate(batches, 1):
            batch_start_time = time.time()
            logger.info(f"Ingesting batch {i}/{len(batches)} ({len(batch)} products)")
            
            try:
                result = ingest_batch(api_url, api_key, batch, session)
                
                # Update stats
                ingestion_stats["batches_sent"] += 1
                ingestion_stats["batches_successful"] += 1
                ingestion_stats["total_inserted"] += result.get("inserted", 0)
                ingestion_stats["total_updated"] += result.get("updated", 0)
                
                # Log batch result
                logger.info(f"Batch {i} successful: {result.get('inserted', 0)} inserted, "
                            f"{result.get('updated', 0)} updated, "
                            f"took {time.time() - batch_start_time:.2f} seconds")
                
                # Verify a random batch occasionally
                if i % 5 == 0 or i == len(batches):
                    product_ids = [p["id"] for p in batch]
                    verification = verify_ingestion(api_url, api_key, product_ids, session)
                    
                    logger.info(f"Verification of batch {i}: checked {verification['checked']} products, "
                               f"found {verification['found']}, missing {verification['missing']}")
                    
                    if verification["missing"] > 0:
                        logger.warning(f"Missing products: {verification['missing_ids']}")
            
            except Exception as e:
                logger.error(f"Error ingesting batch {i}: {str(e)}")
                ingestion_stats["batches_sent"] += 1
                ingestion_stats["total_errors"] += 1
                
                # Continue with next batch despite errors
                continue
            
            # Add a small delay between batches to avoid overwhelming the API
            if i < len(batches):
                time.sleep(0.5)
        
        # Calculate final stats
        ingestion_stats["duration"] = time.time() - ingestion_stats["start_time"]
        ingestion_stats["products_per_second"] = (ingestion_stats["total_inserted"] + 
                                                 ingestion_stats["total_updated"]) / ingestion_stats["duration"]
        
        # Log final stats
        logger.info("Ingestion complete")
        logger.info(f"Total products: {total_products}")
        logger.info(f"Total inserted: {ingestion_stats['total_inserted']}")
        logger.info(f"Total updated: {ingestion_stats['total_updated']}")
        logger.info(f"Total errors: {ingestion_stats['total_errors']}")
        logger.info(f"Duration: {ingestion_stats['duration']:.2f} seconds")
        logger.info(f"Products per second: {ingestion_stats['products_per_second']:.2f}")
        
        if ingestion_stats["total_errors"] > 0:
            logger.warning(f"Not all batches were successful. Check logs for details.")
        
    except Exception as e:
        logger.error(f"Error during ingestion: {str(e)}")
        raise


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Ingest product data into MongoDB Atlas Search API")
    parser.add_argument("--input", required=True, help="Path to the input JSON file")
    parser.add_argument("--api-url", required=True, help="Base URL of the API")
    parser.add_argument("--api-key", required=True, help="API key for authentication")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, 
                       help=f"Number of products to ingest per batch (default: {DEFAULT_BATCH_SIZE})")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    ingest_data(args.input, args.api_url, args.api_key, args.batch_size)
