#!/usr/bin/env python3
"""
Example client for the Product Search and Recommendation API.
This script demonstrates how to interact with all major endpoints.
"""

import requests
import json
import argparse
import os
from pprint import pprint
import sys

# Default API settings
DEFAULT_API_URL = "http://localhost:8000"
DEFAULT_API_KEY = "dev_api_key_12345"  # Should match your .env API_KEY value


class SearchAPIClient:
    """Client for interacting with the Product Search API"""
    
    def __init__(self, api_url, api_key):
        self.api_url = api_url
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json",
            "x-apikey": api_key
        }
    
    def health_check(self):
        """Check if the API is healthy"""
        response = requests.get(f"{self.api_url}/health")
        return response.json()
    
    def ingest_products(self, products):
        """Ingest one or more products"""
        response = requests.post(
            f"{self.api_url}/ingestProducts",
            headers=self.headers,
            json=products
        )
        return response.json() if response.status_code == 201 else None
    
    def ingest_orderline(self, orderline):
        """Ingest an order line"""
        response = requests.post(
            f"{self.api_url}/ingestOrderline",
            headers=self.headers,
            json=orderline
        )
        return response.json() if response.status_code == 201 else None
    
    def search(self, query, filters=None, limit=10, offset=0):
        """Search for products"""
        payload = {
            "query": query,
            "filters": filters or {},
            "limit": limit,
            "offset": offset
        }
        
        response = requests.post(
            f"{self.api_url}/search",
            headers=self.headers,
            json=payload
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Search error: {response.status_code}")
            print(response.text)
            return None
    
    def get_similar_products(self, product_id, limit=5):
        """Get products similar to the specified product ID"""
        payload = {
            "productId": product_id,
            "limit": limit
        }
        
        response = requests.post(
            f"{self.api_url}/similar/{product_id}",
            headers=self.headers,
            json=payload
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Similar products error: {response.status_code}")
            print(response.text)
            return None
    
    def autosuggest(self, prefix, limit=5):
        """Get autosuggestions for a prefix"""
        payload = {
            "prefix": prefix,
            "limit": limit
        }
        
        response = requests.post(
            f"{self.api_url}/autosuggest",
            headers=self.headers,
            json=payload
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Autosuggest error: {response.status_code}")
            print(response.text)
            return None
    
    def get_product(self, product_id):
        """Get a specific product by ID"""
        response = requests.get(
            f"{self.api_url}/doc/{product_id}",
            headers=self.headers
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Get product error: {response.status_code}")
            print(response.text)
            return None
    
    def explain_query(self, query, filters=None):
        """Get explanation for a search query"""
        payload = {
            "query": query,
            "filters": filters or {},
            "limit": 1,
            "offset": 0
        }
        
        response = requests.post(
            f"{self.api_url}/query-explain",
            headers=self.headers,
            json=payload
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Query explain error: {response.status_code}")
            print(response.text)
            return None


def main():
    parser = argparse.ArgumentParser(description="Example client for the Product Search API")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help="API base URL")
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, help="API key for authorization")
    parser.add_argument("--action", choices=["search", "similar", "autosuggest", "explain", "all"], 
                        default="all", help="Action to perform")
    
    args = parser.parse_args()
    
    client = SearchAPIClient(args.api_url, args.api_key)
    
    # Check API health
    print("Checking API health...")
    health = client.health_check()
    print(f"Health status: {json.dumps(health, indent=2)}")
    print()
    
    if health.get("status") != "healthy":
        print("API is not healthy. Exiting.")
        sys.exit(1)
    
    # Perform requested action
    if args.action == "search" or args.action == "all":
        print("Testing search...")
        search_examples = [
            ("baby", {}),
            ("leke", {"ageBucket": "3 to 8 years"}),
            ("rød", {"isOnSale": True})
        ]
        
        for query, filters in search_examples:
            print(f"\nSearching for '{query}' with filters {filters}:")
            results = client.search(query, filters)
            if results:
                print(f"Found {results['total']} results")
                for i, product in enumerate(results["products"][:3]):  # Show first 3 results
                    print(f"{i+1}. {product['title']} ({product['id']}) - {product['priceCurrent']} NOK")
    
    if args.action == "similar" or args.action == "all":
        print("\nTesting similar products recommendations...")
        product_id = "prod1"  # Assuming this product exists
        recommendations = client.get_similar_products(product_id)
        if recommendations:
            print(f"Found {len(recommendations)} recommendations for product {product_id}:")
            for i, product in enumerate(recommendations):
                print(f"{i+1}. {product['title']} ({product['id']})")
    
    if args.action == "autosuggest" or args.action == "all":
        print("\nTesting autosuggest...")
        prefixes = ["ba", "le", "reg"]
        
        for prefix in prefixes:
            print(f"\nGetting suggestions for prefix '{prefix}':")
            suggestions = client.autosuggest(prefix)
            if suggestions:
                print(f"Found {len(suggestions)} suggestions:")
                for i, suggestion in enumerate(suggestions):
                    print(f"{i+1}. {suggestion['title']} ({suggestion['id']})")
    
    if args.action == "explain" or args.action == "all":
        print("\nTesting query explanation...")
        query = "red baby shoes"
        explanation = client.explain_query(query)
        if explanation:
            print(f"Explanation for query '{query}':")
            pprint(explanation)


if __name__ == "__main__":
    main()
