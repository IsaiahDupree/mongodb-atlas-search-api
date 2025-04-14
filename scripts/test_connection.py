#!/usr/bin/env python3
"""
Simple script to verify MongoDB connection and FastAPI application setup
"""
import sys
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.testclient import TestClient
import traceback

# Add app directory to path
APP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")
sys.path.insert(0, APP_DIR)

async def test_mongodb_connection():
    """Test MongoDB connection"""
    print("Testing MongoDB connection...")
    
    # Get MongoDB URI from environment or use default
    mongodb_uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/productdb")
    print(f"Using MongoDB URI: {mongodb_uri}")
    
    try:
        # Connect to MongoDB
        client = AsyncIOMotorClient(mongodb_uri)
        db = client.get_database()
        
        # Test connection with simple ping
        await db.command("ping")
        print("✓ MongoDB connection successful")
        
        # Print available collections
        collections = await db.list_collection_names()
        print(f"Available collections: {collections}")
        
        return True
    except Exception as e:
        print(f"✗ MongoDB connection failed: {str(e)}")
        print(traceback.format_exc())
        return False
    finally:
        if 'client' in locals():
            client.close()

def test_fastapi_app():
    """Test FastAPI application setup"""
    print("\nTesting FastAPI application setup...")
    
    try:
        # Import app
        from main import app
        
        # Create test client
        client = TestClient(app)
        
        # Test health endpoint (should work without authentication)
        response = client.get("/health")
        
        print(f"Health endpoint status code: {response.status_code}")
        if response.status_code == 200:
            print("✓ FastAPI application setup successful")
            print(f"Health check response: {response.json()}")
            return True
        else:
            print(f"✗ Health endpoint failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ FastAPI application setup failed: {str(e)}")
        print(traceback.format_exc())
        return False

async def main():
    """Run tests"""
    print("=== MongoDB Atlas Search API Connection Test ===\n")
    
    # Check current working directory and Python path
    print(f"Current directory: {os.getcwd()}")
    print(f"Python path: {sys.path}\n")
    
    # Test MongoDB connection
    db_success = await test_mongodb_connection()
    
    # Test FastAPI app
    app_success = test_fastapi_app()
    
    # Print summary
    print("\n=== Summary ===")
    print(f"MongoDB Connection: {'✓ Success' if db_success else '✗ Failed'}")
    print(f"FastAPI Setup: {'✓ Success' if app_success else '✗ Failed'}")
    
    return 0 if db_success and app_success else 1
    
if __name__ == "__main__":
    exitcode = asyncio.run(main())
    sys.exit(exitcode)
