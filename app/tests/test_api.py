import os
import sys
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import json

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import app for testing
from main import app

# Create a test client
client = TestClient(app)

# Mock API key for testing
TEST_API_KEY = "test_api_key"

# Sample test data
sample_product = {
    "id": "test1",
    "title": "Test Product",
    "description": "This is a test product",
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

sample_orderline = {
    "orderNr": "ORD-TEST-123",
    "productNr": "test1",
    "customerNr": "cust123",
    "seasonName": "winter",
    "dateTime": "2023-12-15T14:30:00"
}

# Override API key dependency for testing
@pytest.fixture(autouse=True)
def override_dependencies():
    with patch("dependencies.API_KEY", TEST_API_KEY):
        yield

# Tests
def test_health_endpoint():
    """Test the health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_product_ingestion():
    """Test product ingestion endpoint"""
    # Mock database operations
    with patch("routers.products.get_product_collection") as mock_get_collection:
        mock_collection = Mock()
        mock_collection.replace_one.return_value = Mock(upserted_id="test1")
        mock_get_collection.return_value = mock_collection
        
        # Also mock embedding service
        with patch("services.embedding.embedding_service.generate_embedding") as mock_embedding:
            mock_embedding.return_value = [0.1] * 384  # Dummy embedding vector
            
            response = client.post(
                "/ingestProducts",
                headers={"x-apikey": TEST_API_KEY},
                json=[sample_product]
            )
            
            assert response.status_code == 201
            assert "test1" in response.json()

def test_orderline_ingestion():
    """Test orderline ingestion endpoint"""
    # Mock database operations
    with patch("routers.orders.get_orderlines_collection") as mock_get_collection:
        mock_collection = Mock()
        mock_collection.insert_one.return_value = Mock(inserted_id="123")
        mock_get_collection.return_value = mock_collection
        
        response = client.post(
            "/ingestOrderline",
            headers={"x-apikey": TEST_API_KEY},
            json=sample_orderline
        )
        
        assert response.status_code == 201
        assert response.json()["status"] == "success"
        assert response.json()["orderNr"] == sample_orderline["orderNr"]

def test_search_endpoint():
    """Test search endpoint"""
    # Mock database operations for search
    with patch("routers.search.get_product_collection") as mock_get_collection:
        mock_collection = Mock()
        # Mock the aggregate cursor
        mock_cursor = Mock()
        mock_cursor.__aiter__.return_value = [sample_product]
        mock_collection.aggregate.return_value = mock_cursor
        mock_get_collection.return_value = mock_collection
        
        # Mock embedding service
        with patch("services.embedding.embedding_service.generate_embedding") as mock_embedding:
            mock_embedding.return_value = [0.1] * 384  # Dummy embedding vector
            
            response = client.post(
                "/search",
                headers={"x-apikey": TEST_API_KEY},
                json={
                    "query": "test product",
                    "filters": {},
                    "limit": 10,
                    "offset": 0
                }
            )
            
            assert response.status_code == 200
            assert "products" in response.json()
            assert "total" in response.json()
            assert "facets" in response.json()

def test_get_product_endpoint():
    """Test get product endpoint"""
    # Mock database operations
    with patch("routers.products.get_product_collection") as mock_get_collection:
        mock_collection = Mock()
        mock_collection.find_one.return_value = sample_product
        mock_get_collection.return_value = mock_collection
        
        response = client.get(
            "/doc/test1",
            headers={"x-apikey": TEST_API_KEY}
        )
        
        assert response.status_code == 200
        assert response.json()["id"] == "test1"
        assert response.json()["title"] == "Test Product"

def test_similar_products_endpoint():
    """Test similar products endpoint"""
    # Mock database operations
    with patch("routers.orders.get_product_collection") as mock_prod_collection:
        with patch("routers.orders.get_orderlines_collection") as mock_order_collection:
            mock_prod_collection.return_value.find_one.return_value = sample_product
            
            # Mock aggregation pipeline for similar products
            mock_cursor = Mock()
            mock_cursor.__aiter__.return_value = [{"_id": "test2"}]
            mock_order_collection.return_value.aggregate.return_value = mock_cursor
            
            # Mock product retrieval
            mock_product_cursor = Mock()
            mock_product_cursor.__aiter__.return_value = [{"id": "test2", "title": "Similar Product"}]
            mock_prod_collection.return_value.find.return_value = mock_product_cursor
            
            response = client.post(
                "/similar/test1",
                headers={"x-apikey": TEST_API_KEY},
                json={"productId": "test1", "limit": 5}
            )
            
            assert response.status_code == 200
            assert isinstance(response.json(), list)
            if response.json():  # If not empty
                assert response.json()[0]["id"] == "test2"

def test_unauthorized_access():
    """Test that API key is required"""
    response = client.post("/search", json={"query": "test"})
    assert response.status_code == 401  # Unauthorized

if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
