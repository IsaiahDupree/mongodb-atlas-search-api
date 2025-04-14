"""
Test module for naive recommender system endpoints
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
SAMPLE_PRODUCTS = [
    {
        "id": "rec_test_prod1",
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
        "id": "rec_test_prod2",
        "title": "Baby Winter Hat Blue",
        "description": "Warm winter hat for babies, matches with the winter shoes",
        "brand": "TestBrand",
        "imageThumbnailUrl": "https://example.com/test2.jpg",
        "priceOriginal": 99.99,
        "priceCurrent": 79.99,
        "isOnSale": True,
        "ageFrom": 0,
        "ageTo": 1,
        "ageBucket": "0 to 1 years",
        "color": "blue",
        "seasons": ["winter"],
        "productType": "accessory",
        "seasonRelevancyFactor": 0.8,
        "stockLevel": 30
    },
    {
        "id": "rec_test_prod3",
        "title": "Baby Winter Socks Blue",
        "description": "Warm winter socks for babies, perfect with winter shoes",
        "brand": "TestBrand",
        "imageThumbnailUrl": "https://example.com/test3.jpg",
        "priceOriginal": 69.99,
        "priceCurrent": 69.99,
        "isOnSale": False,
        "ageFrom": 0,
        "ageTo": 1,
        "ageBucket": "0 to 1 years",
        "color": "blue",
        "seasons": ["winter"],
        "productType": "accessory",
        "seasonRelevancyFactor": 0.7,
        "stockLevel": 50
    }
]

SAMPLE_ORDERLINES = [
    {
        "orderNr": "REC-TEST-ORD1",
        "productNr": "rec_test_prod1",
        "customerNr": "rec_test_cust1",
        "seasonName": "winter",
        "dateTime": datetime.now().isoformat(),
        "orderLines": {
            "productNr": "rec_test_prod1"
        }
    },
    {
        "orderNr": "REC-TEST-ORD1",
        "productNr": "rec_test_prod2",
        "customerNr": "rec_test_cust1",
        "seasonName": "winter",
        "dateTime": datetime.now().isoformat(),
        "orderLines": {
            "productNr": "rec_test_prod2"
        }
    },
    {
        "orderNr": "REC-TEST-ORD2",
        "productNr": "rec_test_prod1",
        "customerNr": "rec_test_cust2",
        "seasonName": "winter",
        "dateTime": datetime.now().isoformat(),
        "orderLines": {
            "productNr": "rec_test_prod1"
        }
    },
    {
        "orderNr": "REC-TEST-ORD2",
        "productNr": "rec_test_prod3",
        "customerNr": "rec_test_cust2",
        "seasonName": "winter",
        "dateTime": datetime.now().isoformat(),
        "orderLines": {
            "productNr": "rec_test_prod3"
        }
    }
]

# Override API key dependency for testing
@pytest.fixture(autouse=True)
def override_dependencies(monkeypatch):
    """Override API key dependency for testing"""
    monkeypatch.setattr("app.dependencies.API_KEY", TEST_API_KEY)

@pytest.fixture(scope="module")
def setup_recommender_data():
    """Setup test data for recommender system tests"""
    # Ingest test products
    client.post(
        "/ingestProducts",
        headers=HEADERS,
        json=SAMPLE_PRODUCTS
    )
    
    # Ingest test orderlines
    for orderline in SAMPLE_ORDERLINES:
        client.post(
            "/ingestOrderline",
            headers=HEADERS,
            json=orderline
        )
    
    yield
    
    # Clean up
    for product in SAMPLE_PRODUCTS:
        client.delete(
            f"/remove/product/{product['id']}",
            headers=HEADERS
        )

def test_compute_product_pairs(setup_recommender_data):
    """Test computing product pairs for recommendation"""
    response = client.post(
        "/naive-recommender/compute-product-pairs",
        headers=HEADERS
    )
    
    assert response.status_code == 202
    assert "task_id" in response.json()
    assert "status" in response.json()
    assert response.json()["status"] == "processing"

def test_product_pairs_status(setup_recommender_data):
    """Test checking product pairs computation status"""
    # First initiate computation
    client.post(
        "/naive-recommender/compute-product-pairs",
        headers=HEADERS
    )
    
    # Then check status
    response = client.get(
        "/naive-recommender/product-pairs-status",
        headers=HEADERS
    )
    
    assert response.status_code == 200
    assert "status" in response.json()
    assert "last_computed" in response.json()
    assert "pair_count" in response.json()

def test_collaborative_recommendations(setup_recommender_data):
    """Test collaborative recommendations endpoint"""
    # First compute product pairs
    client.post(
        "/naive-recommender/compute-product-pairs",
        headers=HEADERS
    )
    
    # Then get recommendations
    response = client.get(
        "/naive-recommender/user/rec_test_cust1/collaborative",
        headers=HEADERS
    )
    
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    # May be empty if no recommendations, but should be a valid list

def test_content_based_recommendations(setup_recommender_data):
    """Test content-based recommendations endpoint"""
    response = client.get(
        "/naive-recommender/product/rec_test_prod1/content-based",
        headers=HEADERS
    )
    
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    # For our similar winter products, should find something
    if response.json():
        found = False
        for product in response.json():
            if "winter" in product.get("title", "").lower() and product.get("id") != "rec_test_prod1":
                found = True
                break
        assert found, "Should find similar winter products"

def test_hybrid_recommendations(setup_recommender_data):
    """Test hybrid recommendations endpoint"""
    # First compute product pairs
    client.post(
        "/naive-recommender/compute-product-pairs",
        headers=HEADERS
    )
    
    # Then get recommendations
    response = client.get(
        "/naive-recommender/user/rec_test_cust1/hybrid",
        headers=HEADERS,
        params={"limit": 5}
    )
    
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    # Should return a valid list, potentially with recommendations

def test_frequently_bought_together(setup_recommender_data):
    """Test frequently bought together recommendations endpoint"""
    # First compute product pairs
    client.post(
        "/naive-recommender/compute-product-pairs",
        headers=HEADERS
    )
    
    # Then get recommendations
    response = client.get(
        "/naive-recommender/product/rec_test_prod1/frequently-bought-together",
        headers=HEADERS
    )
    
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    # Should find products that were bought together in our sample data

def test_unauthorized_recommender_access():
    """Test unauthorized access is properly rejected"""
    # Try without API key
    response = client.post(
        "/naive-recommender/compute-product-pairs"
    )
    assert response.status_code == 401
    
    # Try with invalid API key
    response = client.post(
        "/naive-recommender/compute-product-pairs",
        headers={"x-apikey": "invalid_key"}
    )
    assert response.status_code == 401

if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
