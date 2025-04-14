#!/usr/bin/env python3
"""
A focused test script for the search endpoint of MongoDB Atlas Search API
"""
import os
import sys
import json
import requests
from pprint import pprint

def test_search_endpoint():
    """Test the search endpoint directly"""
    print("\n===== MongoDB Atlas Search API - Search Endpoint Test =====")
    
    # Setup
    base_url = "http://localhost:8000"
    api_key = os.environ.get("API_KEY", "dev_api_key_12345")
    headers = {"x-apikey": api_key}
    
    # Test search endpoint
    search_url = f"{base_url}/search"
    query = "jacket"
    data = {"query": query, "limit": 5}
    
    print(f"\nSending request to {search_url}")
    print(f"Headers: {headers}")
    print(f"Data: {json.dumps(data, indent=2)}")
    
    try:
        response = requests.post(search_url, json=data, headers=headers, timeout=10)
        
        print(f"\nResponse status code: {response.status_code}")
        
        if response.status_code == 200:
            print("\n✅ Search endpoint test successful!")
            try:
                response_json = response.json()
                print("\nResponse data:")
                pprint(response_json)
                return True
            except json.JSONDecodeError:
                print(f"\nResponse is not valid JSON: {response.text[:200]}")
                return False
        else:
            print(f"\n❌ Search endpoint test failed with status: {response.status_code}")
            print(f"Response text: {response.text}")
            return False
    except Exception as e:
        print(f"\n❌ Error during test: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_search_endpoint()
    sys.exit(0 if success else 1)
