#!/usr/bin/env python3
"""
Simple API testing tool for MongoDB Atlas Search API
This standalone script provides direct testing of API endpoints
"""
import os
import sys
import json
import requests
import argparse
from typing import Dict, List, Any, Optional

class APITester:
    """Test utility for MongoDB Atlas Search API endpoints"""
    
    def __init__(self, base_url: str = "http://localhost:8000", api_key: str = None):
        """Initialize the API tester"""
        self.base_url = base_url
        self.api_key = api_key or os.environ.get("API_KEY", "dev_api_key_12345")
        # Use the correct header name as required by the API (x-apikey not x-api-key)
        self.headers = {"x-apikey": self.api_key}
    
    def test_health(self) -> bool:
        """Test the health endpoint"""
        print(f"\n🔍 Testing health endpoint: {self.base_url}/health")
        
        try:
            response = requests.get(f"{self.base_url}/health", headers=self.headers, timeout=5)
            print(f"Status code: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ Health check successful!")
                print("\nResponse:")
                try:
                    response_json = response.json()
                    print(json.dumps(response_json, indent=2))
                    return True
                except json.JSONDecodeError:
                    print(f"Response (not JSON): {response.text}")
                    return False
            else:
                print(f"❌ Health check failed with status code: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except requests.exceptions.ConnectionError:
            print(f"❌ Connection error: Could not connect to {self.base_url}")
            print("Is the API server running?")
            return False
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return False
    
    def test_search(self, query: str) -> bool:
        """Test the search endpoint"""
        print(f"\n🔍 Testing search endpoint with query: '{query}'")
        
        try:
            url = f"{self.base_url}/search"
            data = {"query": query, "limit": 5}
            
            print(f"Request to {url} with data: {json.dumps(data, indent=2)}")
            response = requests.post(url, json=data, headers=self.headers, timeout=5)
            print(f"Status code: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ Search successful!")
                print("\nResponse (first 500 chars):")
                try:
                    response_json = response.json()
                    print(json.dumps(response_json, indent=2)[:500] + "..." if len(json.dumps(response_json, indent=2)) > 500 else json.dumps(response_json, indent=2))
                    return True
                except json.JSONDecodeError:
                    print(f"Response (not JSON): {response.text[:500]}")
                    return False
            else:
                print(f"❌ Search failed with status code: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except requests.exceptions.ConnectionError:
            print(f"❌ Connection error: Could not connect to {self.base_url}")
            return False
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return False
    
    def test_recommendations(self, product_id: str) -> bool:
        """Test the naive recommender endpoint"""
        print(f"\n🔍 Testing recommendation endpoint for product: '{product_id}'")
        
        try:
            url = f"{self.base_url}/naive-recommender/product/{product_id}/content-based"
            
            print(f"Request to {url}")
            response = requests.get(url, headers=self.headers, timeout=5)
            print(f"Status code: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ Recommendation request successful!")
                print("\nResponse (first 500 chars):")
                try:
                    response_json = response.json()
                    print(json.dumps(response_json, indent=2)[:500] + "..." if len(json.dumps(response_json, indent=2)) > 500 else json.dumps(response_json, indent=2))
                    return True
                except json.JSONDecodeError:
                    print(f"Response (not JSON): {response.text[:500]}")
                    return False
            else:
                print(f"❌ Recommendation request failed with status code: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except requests.exceptions.ConnectionError:
            print(f"❌ Connection error: Could not connect to {self.base_url}")
            return False
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return False

def main():
    """Main function to run the API tester"""
    parser = argparse.ArgumentParser(description='Test the MongoDB Atlas Search API')
    parser.add_argument('--url', type=str, default='http://localhost:8000', 
                      help='Base URL of the API (default: http://localhost:8000)')
    parser.add_argument('--api-key', type=str, default=None,
                      help='API key for authorization (default: from env var API_KEY)')
    parser.add_argument('--test', type=str, choices=['health', 'search', 'recommendations', 'all'], 
                      default='health', help='Test to run (default: health)')
    parser.add_argument('--query', type=str, default='jacket', 
                      help='Search query to use (default: jacket)')
    parser.add_argument('--product-id', type=str, default='P12345', 
                      help='Product ID for recommendation tests (default: P12345)')
    
    args = parser.parse_args()
    
    tester = APITester(args.url, args.api_key)
    
    success = True
    
    if args.test == 'health' or args.test == 'all':
        health_result = tester.test_health()
        success = success and health_result
    
    if args.test == 'search' or args.test == 'all':
        search_result = tester.test_search(args.query)
        success = success and search_result
    
    if args.test == 'recommendations' or args.test == 'all':
        rec_result = tester.test_recommendations(args.product_id)
        success = success and rec_result
    
    if success:
        print("\n✅ All tests completed successfully!")
        return 0
    else:
        print("\n❌ Some tests failed. See details above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
