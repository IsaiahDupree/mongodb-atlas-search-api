# MongoDB Atlas Search API Tests

This directory contains comprehensive tests for the MongoDB Atlas Search API, including the Naive Recommender System.

## Test Coverage

The tests cover all essential API endpoints:

### Product Management
- `POST /ingestProducts` - Ingest product data with embedding generation
- `GET /doc/{product_id}` - Retrieve full product document
- `DELETE /remove/product/{product_id}` - Remove a specific product
- `DELETE /remove/products/all` - Remove all products

### Order Management
- `POST /ingestOrderline` - Ingest order data for recommendations

### Search Functionality
- `POST /search` - Full-featured search with keyword and vector matching
- `POST /autosuggest` - Fast autocomplete suggestions
- `POST /similar/{product_id}` - Find similar products
- `POST /query-explain` - Debug endpoint for query interpretation
- `POST /feedback` - Log user interactions for learning-to-rank

### Naive Recommender System
- Collaborative filtering recommendations
- Content-based recommendations
- Hybrid recommendation approach

### System Endpoints
- `GET /health` - Health check endpoint
- `GET /api-stats` - API usage statistics

## Running Tests

### Prerequisites
- Python 3.9+
- pytest
- pytest-asyncio
- MongoDB running locally or accessible via connection string

### Installation
```bash
pip install pytest pytest-asyncio httpx
```

### Running All Tests
```bash
cd app
python -m pytest tests/test_endpoints.py -v
```

### Running Specific Tests
```bash
python -m pytest tests/test_endpoints.py::test_search -v
python -m pytest tests/test_endpoints.py::test_naive_recommender_endpoints -v
```

## Mock Data

The tests use mock data defined at the top of the test file. You can modify these samples to test different scenarios.

## Test Environment

Tests use a TestClient which simulates HTTP requests to your FastAPI application without actually starting the server. The tests use mocking to avoid actual database operations.

## Authentication

Tests automatically mock the API key authentication with a test key.

## Extending Tests

When adding new endpoints, follow this pattern:
1. Define sample test data
2. Mock necessary dependencies
3. Make the test request
4. Assert the expected response

## Performance Testing

For performance benchmarking beyond unit tests, see the `../scripts/benchmark.py` script.
