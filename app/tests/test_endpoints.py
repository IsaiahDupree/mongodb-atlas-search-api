import os
import sys
import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from typing import Dict, List, Any

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import app for testing
from main import app

# Create a test client
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

SAMPLE_ORDERLINE = {
    "orderNr": "TEST-ORD123",
    "productNr": "test_prod1",
    "customerNr": "test_cust123",
    "seasonName": "winter",
    "dateTime": "2023-12-15T14:30:00"
}

SAMPLE_SEARCH_QUERY = {
    "query": "baby shoes",
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
    "clicked_product_id": "test_prod1",
    "results_shown": ["test_prod1", "test_prod2", "test_prod3"],
    "user_id": "test_user123",
    "session_id": "test_session456"
}

# Override API key dependency for testing
@pytest.fixture(autouse=True)
def override_dependencies():
    with patch("dependencies.API_KEY", TEST_API_KEY):
        yield

# Tests for POST /ingestProducts
def test_ingest_products():
    """Test product ingestion endpoint"""
    # Mock database operations
    with patch("routers.products.get_product_collection") as mock_get_collection:
        mock_collection = Mock()
        mock_collection.replace_one.return_value = Mock(upserted_id="test_prod1")
        mock_get_collection.return_value = mock_collection
        
        # Mock embedding service
        with patch("services.embedding.embedding_service.generate_embedding") as mock_embedding:
            mock_embedding.return_value = [0.1] * 384  # Dummy embedding vector
            
            response = client.post(
                "/ingestProducts",
                headers=HEADERS,
                json=[SAMPLE_PRODUCT]
            )
            
            assert response.status_code == 201
            assert "test_prod1" in response.json()
            
            # Verify that the embedding generation was called correctly
            mock_embedding.assert_any_call(SAMPLE_PRODUCT["title"])
            mock_embedding.assert_any_call(SAMPLE_PRODUCT["description"])

# Tests for POST /ingestOrderline
def test_ingest_orderline():
    """Test orderline ingestion endpoint"""
    # Mock database operations
    with patch("routers.orders.get_orderlines_collection") as mock_get_collection:
        mock_collection = Mock()
        mock_collection.insert_one.return_value = Mock(inserted_id="test123")
        mock_get_collection.return_value = mock_collection
        
        response = client.post(
            "/ingestOrderline",
            headers=HEADERS,
            json=SAMPLE_ORDERLINE
        )
        
        assert response.status_code == 201
        assert response.json()["status"] == "success"
        assert response.json()["orderNr"] == SAMPLE_ORDERLINE["orderNr"]
        assert response.json()["productNr"] == SAMPLE_ORDERLINE["productNr"]

# Tests for POST /search
def test_search():
    """Test search endpoint"""
    # Mock database operations
    with patch("routers.search.get_product_collection") as mock_get_collection:
        mock_collection = Mock()
        
        # Mock the aggregate cursor
        mock_cursor = Mock()
        mock_cursor.__aiter__.return_value = [SAMPLE_PRODUCT]
        mock_collection.aggregate.return_value = mock_cursor
        mock_get_collection.return_value = mock_collection
        
        # Mock embedding service
        with patch("services.embedding.embedding_service.generate_embedding") as mock_embedding:
            mock_embedding.return_value = [0.1] * 384  # Dummy embedding vector
            
            # Mock cache
            with patch("services.cache.search_cache.get") as mock_cache_get:
                mock_cache_get.return_value = None  # No cache hit
                
                with patch("services.cache.search_cache.set") as mock_cache_set:
                    response = client.post(
                        "/search",
                        headers=HEADERS,
                        json=SAMPLE_SEARCH_QUERY
                    )
                    
                    assert response.status_code == 200
                    assert "products" in response.json()
                    assert "total" in response.json()
                    assert "facets" in response.json()
                    
                    # Verify embedding generation was called
                    mock_embedding.assert_called_once_with(SAMPLE_SEARCH_QUERY["query"])

# Tests for POST /autosuggest
def test_autosuggest():
    """Test autosuggest endpoint"""
    # Mock database operations
    with patch("routers.search.get_product_collection") as mock_get_collection:
        mock_collection = Mock()
        
        # Mock suggestions
        suggestions = [
            {"id": "test_prod1", "title": "Baby Shoes", "brand": "TestBrand"},
            {"id": "test_prod2", "title": "Baby Chair", "brand": "TestBrand"}
        ]
        
        # Mock the aggregate cursor
        mock_collection.aggregate.return_value.to_list.return_value = suggestions
        mock_get_collection.return_value = mock_collection
        
        # Mock cache
        with patch("services.cache.search_cache.get") as mock_cache_get:
            mock_cache_get.return_value = None  # No cache hit
            
            with patch("services.cache.search_cache.set") as mock_cache_set:
                response = client.post(
                    "/autosuggest",
                    headers=HEADERS,
                    json=SAMPLE_AUTOSUGGEST_QUERY
                )
                
                assert response.status_code == 200
                assert isinstance(response.json(), list)
                assert len(response.json()) == len(suggestions)
                assert response.json()[0]["id"] == suggestions[0]["id"]

# Tests for POST /similar/{product_id}
def test_similar_products():
    """Test similar products endpoint"""
    # Mock database operations
    with patch("routers.orders.get_product_collection") as mock_prod_collection:
        with patch("routers.orders.get_orderlines_collection") as mock_order_collection:
            # Mock product retrieval
            mock_prod_collection.return_value.find_one.return_value = SAMPLE_PRODUCT
            
            # Mock recommendations generation
            with patch("services.recommendations.RecommendationEngine.get_hybrid_recommendations") as mock_recommendations:
                mock_recommendations.return_value = [
                    {"id": "test_prod2", "title": "Similar Test Product", "brand": "TestBrand"}
                ]
                
                response = client.post(
                    f"/similar/{SAMPLE_PRODUCT['id']}",
                    headers=HEADERS,
                    json={"productId": SAMPLE_PRODUCT['id'], "limit": 5}
                )
                
                assert response.status_code == 200
                assert isinstance(response.json(), list)
                if response.json():  # If not empty
                    assert response.json()[0]["id"] == "test_prod2"

# Tests for GET /doc/{product_id}
def test_get_product():
    """Test get product endpoint"""
    # Mock database operations
    with patch("routers.products.get_product_collection") as mock_get_collection:
        mock_collection = Mock()
        mock_collection.find_one.return_value = SAMPLE_PRODUCT
        mock_get_collection.return_value = mock_collection
        
        response = client.get(
            f"/doc/{SAMPLE_PRODUCT['id']}",
            headers=HEADERS
        )
        
        assert response.status_code == 200
        assert response.json()["id"] == SAMPLE_PRODUCT["id"]
        assert response.json()["title"] == SAMPLE_PRODUCT["title"]
        assert response.json()["description"] == SAMPLE_PRODUCT["description"]

# Tests for GET /health
def test_health():
    """Test health check endpoint"""
    # The health check should not require API key
    with patch("main.app.mongodb.command") as mock_db_command:
        mock_db_command.return_value = True  # Successful ping
        
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert response.json()["database_connection"] == "ok"

# Tests for POST /query-explain
def test_query_explain():
    """Test query explain endpoint"""
    # Mock embedding service
    with patch("services.embedding.embedding_service.generate_embedding") as mock_embedding:
        # Return a simple embedding vector
        mock_embedding.return_value = [0.1] * 384
        
        response = client.post(
            "/query-explain",
            headers=HEADERS,
            json=SAMPLE_SEARCH_QUERY
        )
        
        assert response.status_code == 200
        assert "query_text" in response.json()
        assert response.json()["query_text"] == SAMPLE_SEARCH_QUERY["query"]
        assert "embedding_dimensions" in response.json()
        assert response.json()["embedding_dimensions"] == 384
        assert "cache_info" in response.json()

# Tests for POST /feedback
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

# Tests for DELETE /remove/product/{product_id}
def test_remove_product():
    """Test remove product endpoint"""
    # Mock database operations
    with patch("routers.products.get_product_collection") as mock_get_collection:
        mock_collection = Mock()
        mock_collection.delete_one.return_value = Mock(deleted_count=1)
        mock_get_collection.return_value = mock_collection
        
        response = client.delete(
            f"/remove/product/{SAMPLE_PRODUCT['id']}",
            headers=HEADERS
        )
        
        assert response.status_code == 204
        mock_collection.delete_one.assert_called_once_with({"id": SAMPLE_PRODUCT['id']})

# Tests for DELETE /remove/products/all
def test_remove_all_products():
    """Test remove all products endpoint"""
    # Mock database operations
    with patch("routers.products.get_product_collection") as mock_get_collection:
        mock_collection = Mock()
        mock_collection.delete_many.return_value = Mock(deleted_count=10)
        mock_get_collection.return_value = mock_collection
        
        response = client.delete(
            "/remove/products/all",
            headers=HEADERS
        )
        
        assert response.status_code == 204
        mock_collection.delete_many.assert_called_once_with({})

# Tests for API key authorization
def test_unauthorized_access():
    """Test that API key is required"""
    # Try to access an endpoint without providing an API key
    response = client.post("/search", json=SAMPLE_SEARCH_QUERY)
    assert response.status_code == 401  # Unauthorized

    # Try to access with invalid API key
    response = client.post(
        "/search",
        headers={"x-apikey": "invalid_key"},
        json=SAMPLE_SEARCH_QUERY
    )
    assert response.status_code == 401  # Unauthorized

# Test naive recommender endpoints
def test_naive_recommender_endpoints():
    """Test naive recommender endpoints"""
    # Mock the naive recommender
    with patch("routers.naive_recommender.recommender") as mock_recommender:
        # Mock compute product pairs
        mock_recommender.pre_compute_product_pairs.return_value = {"new_count": 100}
        
        # Mock collaborative recommendations
        mock_recommender.get_collaborative_recommendations.return_value = [
            {"id": "test_prod2", "score": 0.9, "product": SAMPLE_PRODUCT}
        ]
        
        # Mock hybrid recommendations
        mock_recommender.get_hybrid_recommendations.return_value = [
            {"id": "test_prod2", "score": 0.9, "product": SAMPLE_PRODUCT}
        ]
        
        # Test compute product pairs
        response = client.post(
            "/naive-recommender/compute-product-pairs",
            headers=HEADERS
        )
        assert response.status_code == 202
        
        # Test collaborative recommendations
        response = client.get(
            "/naive-recommender/user/test_user123/collaborative",
            headers=HEADERS
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        
        # Test hybrid recommendations
        response = client.get(
            "/naive-recommender/user/test_user123/hybrid",
            headers=HEADERS
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
