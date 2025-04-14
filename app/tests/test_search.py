"""
Test module for search-related endpoints
"""
import pytest
import json
from fastapi.testclient import TestClient

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from dependencies import get_api_key

client = TestClient(app)

# Mock API key for testing
TEST_API_KEY = "test_api_key"
HEADERS = {"x-apikey": TEST_API_KEY}

# Sample test data
SAMPLE_PRODUCTS = [
    {
        "id": "search_test_prod1",
        "title": "Baby Winter Shoes Blue",
        "description": "Comfortable winter shoes for babies, water resistant and warm",
        "brand": "TestBrand",
        "imageThumbnailUrl": "https://example.com/test1.jpg",
        "priceOriginal": 199.99,
        "priceCurrent": 149.99,
        "isOnSale": True,
        "ageFrom": 0,
        "ageTo": 1,
        "ageBucket": "0 to 1 years",
        "color": "blue",
        "seasons": ["winter"],
        "productType": "main",
        "seasonRelevancyFactor": 0.9,
        "stockLevel": 45
    },
    {
        "id": "search_test_prod2",
        "title": "Baby Summer Hat Yellow",
        "description": "Lightweight summer hat with UV protection for babies",
        "brand": "SunCare",
        "imageThumbnailUrl": "https://example.com/test2.jpg",
        "priceOriginal": 99.99,
        "priceCurrent": 79.99,
        "isOnSale": True,
        "ageFrom": 0,
        "ageTo": 2,
        "ageBucket": "0 to 2 years",
        "color": "yellow",
        "seasons": ["summer"],
        "productType": "accessory",
        "seasonRelevancyFactor": 0.7,
        "stockLevel": 30
    },
    {
        "id": "search_test_prod3",
        "title": "Baby Body Lotion",
        "description": "Gentle body lotion for baby's sensitive skin",
        "brand": "BabyCare",
        "imageThumbnailUrl": "https://example.com/test3.jpg",
        "priceOriginal": 129.99,
        "priceCurrent": 129.99,
        "isOnSale": False,
        "ageFrom": 0,
        "ageTo": 3,
        "ageBucket": "0 to 3 years",
        "color": "white",
        "seasons": ["all"],
        "productType": "skincare",
        "seasonRelevancyFactor": 1.0,
        "stockLevel": 100
    }
]

SAMPLE_SEARCH_QUERY = {
    "query": "baby winter",
    "filters": {"color": "blue"},
    "limit": 10,
    "offset": 0
}

SAMPLE_AUTOSUGGEST_QUERY = {
    "prefix": "ba",
    "limit": 5
}

SAMPLE_FEEDBACK = {
    "query": "baby shoes",
    "clicked_product_id": "search_test_prod1",
    "results_shown": ["search_test_prod1", "search_test_prod2", "search_test_prod3"],
    "user_id": "test_user123",
    "session_id": "test_session456"
}

# Override API key dependency for testing
@pytest.fixture(autouse=True)
def override_dependencies(monkeypatch):
    """Override API key dependency for testing"""
    monkeypatch.setattr("app.dependencies.API_KEY", TEST_API_KEY)

@pytest.fixture(scope="module")
def setup_test_data():
    """Set up test products for search testing"""
    # Ingest test products
    client.post(
        "/ingestProducts",
        headers=HEADERS,
        json=SAMPLE_PRODUCTS
    )
    
    yield
    
    # Clean up
    for product in SAMPLE_PRODUCTS:
        client.delete(
            f"/remove/product/{product['id']}",
            headers=HEADERS
        )

def test_search(setup_test_data):
    """Test full search functionality"""
    response = client.post(
        "/search",
        headers=HEADERS,
        json=SAMPLE_SEARCH_QUERY
    )
    
    assert response.status_code == 200
    result = response.json()
    assert "products" in result
    assert "total" in result
    assert "facets" in result
    assert isinstance(result["products"], list)

def test_search_with_filters(setup_test_data):
    """Test search with filters"""
    query = {
        "query": "baby",
        "filters": {"brand": "BabyCare"},
        "limit": 10,
        "offset": 0
    }
    
    response = client.post(
        "/search",
        headers=HEADERS,
        json=query
    )
    
    assert response.status_code == 200
    result = response.json()
    
    # If results are found, they should match the filter
    if result["products"]:
        assert any(p["brand"] == "BabyCare" for p in result["products"])

def test_autosuggest(setup_test_data):
    """Test autosuggest endpoint"""
    response = client.post(
        "/autosuggest",
        headers=HEADERS,
        json=SAMPLE_AUTOSUGGEST_QUERY
    )
    
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    # Should match the prefix "ba" in products like "Baby"
    if response.json():
        for suggestion in response.json():
            assert "title" in suggestion
            assert suggestion["title"].lower().startswith(SAMPLE_AUTOSUGGEST_QUERY["prefix"].lower()) or \
                   "baby" in suggestion["title"].lower()  # Testing both prefix and tokenized matching

def test_query_explain():
    """Test query explain debugging endpoint"""
    response = client.post(
        "/query-explain",
        headers=HEADERS,
        json=SAMPLE_SEARCH_QUERY
    )
    
    assert response.status_code == 200
    result = response.json()
    assert "query_text" in result
    assert result["query_text"] == SAMPLE_SEARCH_QUERY["query"]
    assert "embedding_dimensions" in result
    assert "cache_info" in result

def test_feedback():
    """Test feedback logging endpoint"""
    response = client.post(
        "/feedback",
        headers=HEADERS,
        json=SAMPLE_FEEDBACK
    )
    
    assert response.status_code == 200
    assert "status" in response.json()
    assert response.json()["status"] == "feedback received"

def test_unauthorized_search_access():
    """Test unauthorized access is properly rejected"""
    # Try without API key
    response = client.post(
        "/search",
        json=SAMPLE_SEARCH_QUERY
    )
    assert response.status_code == 401
    
    # Try with invalid API key
    response = client.post(
        "/search",
        headers={"x-apikey": "invalid_key"},
        json=SAMPLE_SEARCH_QUERY
    )
    assert response.status_code == 401

if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
