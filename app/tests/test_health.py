"""
Test module for health and system monitoring endpoints
"""
import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock

# Import test utilities
from tests.test_utils import get_test_patches, TEST_API_KEY, TEST_HEADERS

# Import app directly - our patches will handle the database mocking
from main import app

# Create a test client
client = TestClient(app)
HEADERS = TEST_HEADERS

@pytest.fixture(scope="module", autouse=True)
def apply_test_patches():
    """Apply all test patches needed for the health tests"""
    patches = get_test_patches()
    for p in patches:
        p.start()
    
    # Mock the FastAPI lifespan to avoid actual DB connections
    with patch("main.lifespan"):
        yield
    
    for p in patches:
        p.stop()

def test_health_endpoint():
    """Test health check endpoint - should be accessible without API key
    and return system health status"""
    # Mock the db command function to return expected health data
    with patch("database.mongodb.db.db.command") as mock_command:
        mock_command.return_value = {"ok": 1, "version": "5.0.0"}
        
        response = client.get("/health")
        
        assert response.status_code == 200
        result = response.json()
        assert "status" in result
        assert result["status"] == "healthy"
        assert "database_connection" in result
        
        # Check that additional health info is present
        assert "timestamp" in result
        assert "services" in result

def test_api_stats_endpoint():
    """
    Test API statistics endpoint - should require API key
    and return usage statistics
    """
    # Test with valid API key
    response = client.get(
        "/api-stats",
        headers=HEADERS
    )
    
    assert response.status_code == 200
    result = response.json()
    assert "search_metrics" in result
    
    # Test without API key (should fail)
    response = client.get("/api-stats")
    assert response.status_code == 401
    
    # Test with invalid API key (should fail)
    response = client.get(
        "/api-stats",
        headers={"x-apikey": "invalid_key"}
    )
    assert response.status_code == 401

def test_response_headers():
    """Test that processing time header is included in responses"""
    response = client.get("/health")
    
    assert "X-Process-Time" in response.headers
    # Process time should be a positive number
    process_time = float(response.headers["X-Process-Time"])
    assert process_time > 0

def test_health_endpoint_detailed_info():
    """Test that health endpoint provides detailed system information"""
    response = client.get("/health")
    
    assert response.status_code == 200
    result = response.json()
    
    # Check for detailed MongoDB information if available
    if "services" in result and "mongodb" in result["services"]:
        mongodb_info = result["services"]["mongodb"]
        
        # If collections info is available, verify structure
        if "collections" in mongodb_info:
            collections = mongodb_info["collections"]
            for collection_name, stats in collections.items():
                assert "count" in stats
                assert "size_mb" in stats

if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
