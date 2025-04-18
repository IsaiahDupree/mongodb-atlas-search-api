import pytest
from fastapi.testclient import TestClient
import json
from unittest.mock import patch, MagicMock
import os
import sys

# Add the parent directory to sys.path to allow importing from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from services.embedding import embedding_service
from models.product import CategoryResult, BrandResult

client = TestClient(app)

# Sample test data
test_query = "metaldetector"
sample_categories = [
    CategoryResult(id="cat1", name="Metal Detectors", slug="metal-detectors", productCount=5),
    CategoryResult(id="cat2", name="Outdoor Equipment", slug="outdoor-equipment", productCount=2)
]
sample_brands = [
    BrandResult(id="brand1", name="MetalTech", productCount=3),
    BrandResult(id="brand2", name="DetectorPro", productCount=2)
]
sample_products = [
    {
        "id": "prod1",
        "title": "Professional Metal Detector",
        "description": "High-sensitivity metal detector for professionals",
        "brand": "MetalTech",
        "imageThumbnailUrl": "https://example.com/img1.jpg",
        "priceOriginal": 299.99,
        "priceCurrent": 249.99,
        "isOnSale": True,
        "score": 5.0,
        "matchType": "exact"
    },
    {
        "id": "prod2",
        "title": "Beginner Metal Detector",
        "description": "Easy to use metal detector for beginners",
        "brand": "DetectorPro",
        "imageThumbnailUrl": "https://example.com/img2.jpg",
        "priceOriginal": 149.99,
        "priceCurrent": 149.99,
        "isOnSale": False,
        "score": 4.5,
        "matchType": "ngram"
    }
]

# Mock async functions
@pytest.fixture
def mock_search_functions():
    with patch("routers.search.search_categories") as mock_categories, \
         patch("routers.search.search_brands") as mock_brands, \
         patch("routers.search.search_products_consolidated") as mock_products, \
         patch("services.embedding.embedding_service.generate_embedding") as mock_embedding:
        
        mock_categories.return_value = sample_categories
        mock_brands.return_value = sample_brands
        mock_products.return_value = sample_products
        mock_embedding.return_value = [0.1] * 384  # Mock 384-dimensional vector
        
        yield {
            "categories": mock_categories,
            "brands": mock_brands,
            "products": mock_products,
            "embedding": mock_embedding
        }

def test_consolidated_search_validation():
    """Test validation of minimum query length requirement"""
    # Test with query that's too short
    response = client.post(
        "/consolidated-search",
        json={"query": "me", "maxCategories": 5, "maxBrands": 5, "maxProducts": 10}
    )
    assert response.status_code == 400
    assert "at least 3 characters" in response.json()["detail"]

@pytest.mark.asyncio
async def test_consolidated_search(mock_search_functions):
    """Test consolidated search endpoint with mocked search functions"""
    # Test with valid query
    response = client.post(
        "/consolidated-search",
        json={
            "query": test_query,
            "maxCategories": 5,
            "maxBrands": 5,
            "maxProducts": 10,
            "includeVectorSearch": True
        }
    )
    
    assert response.status_code == 200
    result = response.json()
    
    # Check structure of response
    assert "categories" in result
    assert "brands" in result
    assert "products" in result
    assert "metadata" in result
    
    # Check content of response
    assert len(result["categories"]) == len(sample_categories)
    assert len(result["brands"]) == len(sample_brands)
    assert len(result["products"]) == len(sample_products)
    
    # Check that categories match expected structure
    for i, category in enumerate(result["categories"]):
        assert category["id"] == sample_categories[i].id
        assert category["name"] == sample_categories[i].name
        assert category["slug"] == sample_categories[i].slug
        assert category["productCount"] == sample_categories[i].productCount
    
    # Check that brands match expected structure
    for i, brand in enumerate(result["brands"]):
        assert brand["id"] == sample_brands[i].id
        assert brand["name"] == sample_brands[i].name
        assert brand["productCount"] == sample_brands[i].productCount
    
    # Check that products match expected structure
    for i, product in enumerate(result["products"]):
        assert product["id"] == sample_products[i]["id"]
        assert product["title"] == sample_products[i]["title"]
        assert product["brand"] == sample_products[i]["brand"]
        assert product["matchType"] == sample_products[i]["matchType"]
    
    # Check that metadata contains expected fields
    assert "totalResults" in result["metadata"]
    assert "processingTimeMs" in result["metadata"]
    assert "query" in result["metadata"]
    assert result["metadata"]["query"] == test_query
    assert result["metadata"]["totalResults"] == len(sample_categories) + len(sample_brands) + len(sample_products)

@pytest.mark.asyncio
async def test_consolidated_search_without_vector(mock_search_functions):
    """Test consolidated search endpoint with vector search disabled"""
    response = client.post(
        "/consolidated-search",
        json={
            "query": test_query,
            "maxCategories": 3,
            "maxBrands": 3,
            "maxProducts": 5,
            "includeVectorSearch": False
        }
    )
    
    assert response.status_code == 200
    # Verify the embedding generation was not called when vector search is disabled
    mock_search_functions["embedding"].assert_not_called()

@pytest.mark.asyncio
async def test_consolidated_search_partial_word_matching(mock_search_functions):
    """Test that partial word matches like 'met', 'meta', etc. work as expected"""
    # List of partial searches that should match "metaldetector"
    partial_searches = ["met", "meta", "metall", "metalde", "metaldetect"]
    
    for partial in partial_searches:
        response = client.post(
            "/consolidated-search",
            json={"query": partial, "maxCategories": 2, "maxBrands": 2, "maxProducts": 5}
        )
        
        assert response.status_code == 200
        result = response.json()
        
        # Even with partial match, we should get results
        assert len(result["products"]) > 0
        
        # The search functions should have been called with the partial query
        mock_search_functions["categories"].assert_called_with(
            app.mongodb, 
            app.mongodb.products, 
            partial, 
            2
        )
        mock_search_functions["brands"].assert_called_with(
            app.mongodb, 
            app.mongodb.products, 
            partial, 
            2
        )
        mock_search_functions["products"].assert_called_with(
            app.mongodb, 
            app.mongodb.products, 
            partial, 
            mock_search_functions["embedding"].return_value, 
            5,
            True
        )
