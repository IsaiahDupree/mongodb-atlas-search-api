#!/usr/bin/env python3
"""
A simple standalone script to verify that our health endpoint works.
This script bypasses the complex test frameworks and directly connects to the API.
"""
import os
import sys
import json
import requests
from unittest.mock import patch

def test_health_endpoint():
    """
    Test the health endpoint by directly calling it using requests
    """
    print("MongoDB Atlas Search API - Health Endpoint Test")
    print("==============================================")
    
    # Define the base URL for the API
    base_url = os.environ.get("API_URL", "http://localhost:8000")
    
    # Set up environment for testing
    os.environ["TESTING"] = "true"
    
    # Check if the server is running
    try:
        print(f"Testing health endpoint at {base_url}/health...")
        response = requests.get(f"{base_url}/health", timeout=5)
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Health check successful!")
            print("\nResponse body:")
            response_json = response.json()
            print(json.dumps(response_json, indent=2))
            
            # Verify expected fields
            if response_json.get("status") == "healthy":
                print("\n✅ Status is 'healthy'")
            else:
                print("\n❌ Status is not 'healthy'")
                
            if "database_connection" in response_json:
                print("✅ Database connection info is present")
            else:
                print("❌ Database connection info is missing")
                
            return True
        else:
            print(f"❌ Health check failed with status code: {response.status_code}")
            print("\nResponse body:")
            print(response.text)
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection error: Could not connect to {base_url}")
        print("Is the API server running? Use 'uvicorn main:app --reload' to start it.")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_health_endpoint()
    sys.exit(0 if success else 1)
