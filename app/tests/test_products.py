"""
Test module for product-related endpoints
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

def test_ingest_products():
    """Test product ingestion endpoint"""
    response = client.post(
        "/ingestProducts",
        headers=HEADERS,
        json=[SAMPLE_PRODUCT]
    )
    
    assert response.status_code == 201
    assert isinstance(response.json(), list)
    assert len(response.json()) > 0, "Should return at least one product ID"

def test_get_product():
    """Test get product endpoint"""
    # First ingest a product
    client.post(
        "/ingestProducts",
        headers=HEADERS,
        json=[SAMPLE_PRODUCT]
    )
    
    # Then retrieve it
    response = client.get(
        f"/doc/{SAMPLE_PRODUCT['id']}",
        headers=HEADERS
    )
    
    assert response.status_code == 200
    assert response.json()["id"] == SAMPLE_PRODUCT["id"]
    assert response.json()["title"] == SAMPLE_PRODUCT["title"]

def test_get_nonexistent_product():
    """Test getting a product that doesn't exist"""
    response = client.get(
        "/doc/nonexistent_product_id",
        headers=HEADERS
    )
    
    assert response.status_code == 404

def test_remove_product():
    """Test remove product endpoint"""
    # First ingest a product
    client.post(
        "/ingestProducts",
        headers=HEADERS,
        json=[SAMPLE_PRODUCT]
    )
    
    # Then delete it
    response = client.delete(
        f"/remove/product/{SAMPLE_PRODUCT['id']}",
        headers=HEADERS
    )
    
    assert response.status_code == 204
    
    # Verify it's gone
    get_response = client.get(
        f"/doc/{SAMPLE_PRODUCT['id']}",
        headers=HEADERS
    )
    
    assert get_response.status_code == 404

def test_remove_all_products():
    """Test remove all products endpoint"""
    # First ingest multiple products
    products = [
        SAMPLE_PRODUCT,
        {**SAMPLE_PRODUCT, "id": "test_prod2", "title": "Test Baby Chair"}
    ]
    
    client.post(
        "/ingestProducts",
        headers=HEADERS,
        json=products
    )
    
    # Then delete all
    response = client.delete(
        "/remove/products/all",
        headers=HEADERS
    )
    
    assert response.status_code == 204
    
    # Verify they're gone
    for product in products:
        get_response = client.get(
            f"/doc/{product['id']}",
            headers=HEADERS
        )
        assert get_response.status_code == 404

def test_unauthorized_product_access():
    """Test unauthorized access is properly rejected"""
    # Try without API key
    response = client.post(
        "/ingestProducts",
        json=[SAMPLE_PRODUCT]
    )
    assert response.status_code == 401
    
    # Try with invalid API key
    response = client.post(
        "/ingestProducts",
        headers={"x-apikey": "invalid_key"},
        json=[SAMPLE_PRODUCT]
    )
    assert response.status_code == 401

if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
