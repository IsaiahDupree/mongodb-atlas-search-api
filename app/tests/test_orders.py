"""
Test module for order-related endpoints
"""
import pytest
import json
from fastapi.testclient import TestClient
from datetime import datetime

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
SAMPLE_ORDERLINE = {
    "orderNr": "TEST-ORD123",
    "productNr": "test_prod1",
    "customerNr": "test_cust123",
    "seasonName": "winter",
    "dateTime": datetime.now().isoformat()
}

SAMPLE_PRODUCT = {
    "id": "test_prod1",
    "title": "Test Baby Shoes",
    "description": "Comfortable test shoes for babies",
    "brand": "TestBrand",
    "imageThumbnailUrl": "https://example.com/test.jpg",
    "priceOriginal": 199.99,
    "priceCurrent": 149.99,
    "isOnSale": True,
    "ageFrom": 1,
    "ageTo": 3,
    "ageBucket": "1 to 3 years",
    "color": "blue",
    "seasons": ["winter", "spring"],
    "productType": "main",
    "seasonRelevancyFactor": 0.8,
    "stockLevel": 45
}

# Override API key dependency for testing
@pytest.fixture(autouse=True)
def override_dependencies(monkeypatch):
    """Override API key dependency for testing"""
    monkeypatch.setattr("app.dependencies.API_KEY", TEST_API_KEY)

@pytest.fixture(scope="module")
def setup_product():
    """Set up a product for testing orderlines"""
    response = client.post(
        "/ingestProducts",
        headers=HEADERS,
        json=[SAMPLE_PRODUCT]
    )
    
    yield SAMPLE_PRODUCT
    
    # Clean up
    client.delete(
        f"/remove/product/{SAMPLE_PRODUCT['id']}",
        headers=HEADERS
    )

def test_ingest_orderline(setup_product):
    """Test orderline ingestion endpoint"""
    response = client.post(
        "/ingestOrderline",
        headers=HEADERS,
        json=SAMPLE_ORDERLINE
    )
    
    assert response.status_code == 201
    assert response.json()["status"] == "success"
    assert response.json()["orderNr"] == SAMPLE_ORDERLINE["orderNr"]
    assert response.json()["productNr"] == SAMPLE_ORDERLINE["productNr"]

def test_ingest_orderline_with_nonexistent_product():
    """Test orderline ingestion with a product that doesn't exist"""
    orderline = {
        **SAMPLE_ORDERLINE,
        "productNr": "nonexistent_product"
    }
    
    response = client.post(
        "/ingestOrderline",
        headers=HEADERS,
        json=orderline
    )
    
    # Should still succeed as we don't validate product existence
    assert response.status_code == 201
    assert response.json()["status"] == "success"

def test_similar_products(setup_product):
    """Test similar products endpoint"""
    # First ingest an orderline
    client.post(
        "/ingestOrderline",
        headers=HEADERS,
        json=SAMPLE_ORDERLINE
    )
    
    # Then get similar products
    response = client.post(
        f"/similar/{SAMPLE_PRODUCT['id']}",
        headers=HEADERS,
        json={"productId": SAMPLE_PRODUCT['id'], "limit": 5}
    )
    
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    # May be empty if no similar products, but should be a valid response

def test_similar_products_with_invalid_id():
    """Test similar products endpoint with invalid product ID"""
    response = client.post(
        "/similar/nonexistent_product",
        headers=HEADERS,
        json={"productId": "nonexistent_product", "limit": 5}
    )
    
    # Should return 404 as the product doesn't exist
    assert response.status_code == 404

def test_unauthorized_orderline_access():
    """Test unauthorized access is properly rejected"""
    # Try without API key
    response = client.post(
        "/ingestOrderline",
        json=SAMPLE_ORDERLINE
    )
    assert response.status_code == 401
    
    # Try with invalid API key
    response = client.post(
        "/ingestOrderline",
        headers={"x-apikey": "invalid_key"},
        json=SAMPLE_ORDERLINE
    )
    assert response.status_code == 401

if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
