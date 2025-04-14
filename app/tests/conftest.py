"""Pytest configuration file for MongoDB Atlas Search API tests."""
import pytest
import sys
import os
from typing import Generator
from unittest.mock import patch, Mock
import asyncio
from contextlib import asynccontextmanager

# Add app directory to path to enable proper imports
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Import mock database module
from tests.mock_db import get_mock_db_patch

# Mock environment variables for testing
os.environ["MONGODB_URI"] = "mongodb://localhost:27017/test_db"
os.environ["API_KEY"] = "test_api_key"
TEST_API_KEY = "test_api_key"

# Apply mock database patches globally for all tests
@pytest.fixture(scope="session", autouse=True)
def mock_mongodb():
    """Apply mock database patches for all tests"""
    patches = get_mock_db_patch()
    
    # Start all patches
    for p in patches:
        p.start()
    
    yield
    
    # Stop all patches
    for p in patches:
        p.stop()

# Mock the FastAPI lifespan to avoid actual DB connections
@pytest.fixture(scope="session", autouse=True)
def mock_lifespan():
    """Mock the FastAPI lifespan to avoid actual DB connections"""
    @asynccontextmanager
    async def mock_lifespan_cm(_):
        # No actual DB connection
        yield
    
    with patch("main.lifespan", mock_lifespan_cm):
        yield

@pytest.fixture
def mock_embedding_service():
    """Mock the embedding service"""
    with patch("services.embedding.embedding_service.generate_embedding") as mock:
        mock.return_value = [0.1] * 384  # Standard embedding dimension
        yield mock

@pytest.fixture
def mock_cache_service():
    """Mock the caching service"""
    with patch("services.cache.search_cache") as mock_cache:
        mock_cache.get.return_value = None  # No cache hit by default
        mock_cache.set = Mock()
        mock_cache.get_stats.return_value = {"hits": 0, "misses": 0}
        yield mock_cache

@pytest.fixture
def test_client():
    """Create a test client for the FastAPI application"""
    from fastapi.testclient import TestClient
    # Import the app after mock_mongodb fixture has been applied
    from main import app
    
    # Override API key dependency for testing
    with patch("dependencies.API_KEY", TEST_API_KEY):
        client = TestClient(app)
        yield client

@pytest.fixture(autouse=True)
def override_dependencies():
    """Override dependencies for testing"""
    with patch("dependencies.API_KEY", TEST_API_KEY):
        yield
