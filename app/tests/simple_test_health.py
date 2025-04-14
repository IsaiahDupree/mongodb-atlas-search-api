"""
Simple standalone test for the health endpoint
"""
import os
import sys
import json
from unittest.mock import patch

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Import TestClient directly (will be used with patched dependencies)
from fastapi.testclient import TestClient

# Test constants
TEST_API_KEY = "test_api_key"

def run_health_endpoint_test():
    """
    Run a simple test for the health endpoint without complex pytest fixtures
    """
    # Import app after patching environment variables
    os.environ["API_KEY"] = TEST_API_KEY
    os.environ["MONGODB_URI"] = "mongodb://localhost:27017/testdb"
    
    # Create patches for database dependencies
    # This will prevent actual MongoDB connections
    mock_patches = []
    
    try:
        # Patch the MongoDB client creation in the lifespan
        with patch("motor.motor_asyncio.AsyncIOMotorClient") as mock_client:
            # Mock the database connection
            mock_db = mock_client.return_value.__getitem__.return_value
            mock_db.command.return_value = {"ok": 1}
            mock_db.list_collection_names.return_value = ["products", "orderlines", "product_pairs"]
            
            # Add command stats for collections
            mock_db.command.side_effect = lambda cmd, coll=None, **kwargs: (
                {"ok": 1, "count": 100, "size": 1024 * 1024} if cmd == "collStats" else {"ok": 1}
            )
            
            # Now import the app with mocks in place
            from main import app
            
            # Set testing environment variable
            os.environ["TESTING"] = "true"
            
            # Create test client - use proper initialization for FastAPI
            from starlette.testclient import TestClient
            client = TestClient(app=app)
            
            # Test health endpoint
            print("Testing /health endpoint...")
            response = client.get("/health")
            
            # Print results
            print(f"Status code: {response.status_code}")
            print("Response body:")
            print(json.dumps(response.json(), indent=2))
            
            # Basic assertions
            if response.status_code == 200:
                print("✅ Test PASSED: Status code is 200")
            else:
                print("❌ Test FAILED: Status code is not 200")
                
            result = response.json()
            if result.get("status") == "healthy":
                print("✅ Test PASSED: Status is 'healthy'")
            else:
                print("❌ Test FAILED: Status is not 'healthy'")
                
            if "database_connection" in result:
                print("✅ Test PASSED: Database connection info is present")
            else:
                print("❌ Test FAILED: Database connection info is missing")
            
            print("\nTest completed!")
            return response.status_code == 200
            
    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_health_endpoint_test()
    sys.exit(0 if success else 1)
