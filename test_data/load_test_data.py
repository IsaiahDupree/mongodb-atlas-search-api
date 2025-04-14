#!/usr/bin/env python3
"""
Test script to load sample data into the MongoDB database and test the API endpoints.
This can be run either inside the container or on the host machine.
"""

import json
import requests
import os
import argparse
from datetime import datetime

# Default values
DEFAULT_API_URL = "http://localhost:8000"
DEFAULT_API_KEY = "dev_api_key_12345"  # Should match the value in .env

def load_products(api_url, api_key):
    """Load sample products into the database"""
    print("Loading sample products...")
    
    # Read product data from file
    with open("sample_products.json", "r", encoding="utf-8") as f:
        products = json.load(f)
    
    # Send products to the API
    headers = {
        "Content-Type": "application/json",
        "x-apikey": api_key
    }
    
    response = requests.post(
        f"{api_url}/ingestProducts",
        headers=headers,
        json=products
    )
    
    if response.status_code == 201:
        print(f"Successfully loaded {len(products)} products")
        print(f"Product IDs: {response.json()}")
    else:
        print(f"Error loading products: {response.status_code}")
        print(response.text)
        
def load_orderlines(api_url, api_key):
    """Load sample orderlines into the database"""
    print("Loading sample orderlines...")
    
    # Read orderlines data from file
    with open("sample_orderlines.json", "r", encoding="utf-8") as f:
        orderlines = json.load(f)
    
    # Send orderlines to the API
    headers = {
        "Content-Type": "application/json",
        "x-apikey": api_key
    }
    
    success_count = 0
    
    for orderline in orderlines:
        response = requests.post(
            f"{api_url}/ingestOrderline",
            headers=headers,
            json=orderline
        )
        
        if response.status_code == 201:
            success_count += 1
        else:
            print(f"Error loading orderline {orderline['orderNr']}: {response.status_code}")
            print(response.text)
    
    print(f"Successfully loaded {success_count}/{len(orderlines)} orderlines")

def test_search(api_url, api_key):
    """Test the search endpoint"""
    print("\nTesting search functionality...")
    
    # Test basic search
    headers = {
        "Content-Type": "application/json",
        "x-apikey": api_key
    }
    
    # Test queries
    test_queries = [
        {"query": "baby", "filters": {}},
        {"query": "rød", "filters": {"ageBucket": "1 to 3 years"}},
        {"query": "barnevogn", "filters": {"isOnSale": True}}
    ]
    
    for query_data in test_queries:
        print(f"\nSearching for: '{query_data['query']}' with filters: {query_data['filters']}")
        
        response = requests.post(
            f"{api_url}/search",
            headers=headers,
            json={
                "query": query_data["query"],
                "filters": query_data["filters"],
                "limit": 10,
                "offset": 0
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"Found {result['total']} results")
            for i, product in enumerate(result["products"]):
                print(f"{i+1}. {product['title']} ({product['id']}) - {product['priceCurrent']} NOK")
        else:
            print(f"Error searching: {response.status_code}")
            print(response.text)

def test_recommendations(api_url, api_key):
    """Test the product recommendations"""
    print("\nTesting product recommendations...")
    
    headers = {
        "Content-Type": "application/json",
        "x-apikey": api_key
    }
    
    # Test with product that has recommendations
    product_id = "prod1"
    print(f"Getting recommendations for product: {product_id}")
    
    response = requests.post(
        f"{api_url}/similar/{product_id}",
        headers=headers,
        json={"productId": product_id, "limit": 5}
    )
    
    if response.status_code == 200:
        recommendations = response.json()
        print(f"Found {len(recommendations)} recommendations:")
        for i, product in enumerate(recommendations):
            print(f"{i+1}. {product['title']} ({product['id']})")
    else:
        print(f"Error getting recommendations: {response.status_code}")
        print(response.text)

def test_autosuggest(api_url, api_key):
    """Test the autosuggest endpoint"""
    print("\nTesting autosuggest functionality...")
    
    headers = {
        "Content-Type": "application/json",
        "x-apikey": api_key
    }
    
    # Test with prefix
    prefixes = ["ba", "le", "reg"]
    
    for prefix in prefixes:
        print(f"\nGetting suggestions for prefix: '{prefix}'")
        
        response = requests.post(
            f"{api_url}/autosuggest",
            headers=headers,
            json={"prefix": prefix, "limit": 5}
        )
        
        if response.status_code == 200:
            suggestions = response.json()
            print(f"Found {len(suggestions)} suggestions:")
            for i, suggestion in enumerate(suggestions):
                print(f"{i+1}. {suggestion['title']} ({suggestion['id']})")
        else:
            print(f"Error getting suggestions: {response.status_code}")
            print(response.text)

def main():
    parser = argparse.ArgumentParser(description="Load test data and test API endpoints")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help="API base URL")
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, help="API key for authorization")
    parser.add_argument("--load-only", action="store_true", help="Only load data, don't test endpoints")
    parser.add_argument("--test-only", action="store_true", help="Only test endpoints, don't load data")
    
    args = parser.parse_args()
    
    # Make sure we're in the right directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Test health endpoint first
    print(f"Testing API health at {args.api_url}/health...")
    try:
        response = requests.get(f"{args.api_url}/health")
        if response.status_code == 200:
            print("API is healthy!")
        else:
            print(f"API health check failed: {response.status_code}")
            print(response.text)
            return
    except requests.RequestException as e:
        print(f"Error connecting to API: {e}")
        print("Make sure the API is running and accessible.")
        return
    
    # Load data if requested
    if not args.test_only:
        load_products(args.api_url, args.api_key)
        load_orderlines(args.api_url, args.api_key)
    
    # Test endpoints if requested
    if not args.load_only:
        test_search(args.api_url, args.api_key)
        test_recommendations(args.api_url, args.api_key)
        test_autosuggest(args.api_url, args.api_key)
    
if __name__ == "__main__":
    main()
