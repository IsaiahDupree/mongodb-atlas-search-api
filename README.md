# Dockerized MongoDB Atlas Search API

A containerized search and ingest API for MongoDB Atlas with vector search capabilities, built with FastAPI and Docker.

## Features

- Vector search for product data using MongoDB Atlas Search with knnBeta
- Local embeddings generation using `paraphrase-multilingual-MiniLM-L12-v2` model (optimized for Norwegian and Swedish)
- Faceted search results for e-commerce applications
- Product recommendations based on purchase history
- Simple API key authorization
- Dockerized deployment with MongoDB and FastAPI

## Prerequisites

- Docker and Docker Compose
- MongoDB Atlas account (optional, can use local MongoDB instead)
- Python 3.9+ (for local development)

## Quick Start

1. Clone the repository
2. Create a `.env` file from the example
   ```bash
   cp .env.example .env
   ```
3. Update the `.env` file with your MongoDB Atlas connection string (if using Atlas)
4. Build and start the containers
   ```bash
   docker-compose up -d --build
   ```
5. Access the API documentation at http://localhost:8000/docs

## Configuration

### Environment Variables

- `MONGODB_URI`: MongoDB connection string 
  - Local: `mongodb://mongodb:27017/productdb`
  - Atlas: `mongodb+srv://<username>:<password>@<cluster>.mongodb.net/productdb?retryWrites=true&w=majority`
- `API_KEY`: Secret API key for authorization

## MongoDB Atlas Setup

For production use with MongoDB Atlas:

1. Create a MongoDB Atlas cluster if you don't have one
2. Create a vector search index on the `products` collection
   - Index name: `product_search`
   - Configure vector fields:
     - `title_embedding`: 384 dimensions, cosine similarity
     - `description_embedding`: 384 dimensions, cosine similarity

## API Endpoints

### Products

- `POST /ingest/products`: Ingest product data with automatic embedding generation
- `GET /doc/{product_id}`: Retrieve a specific product by ID
- `DELETE /remove/product/{product_id}`: Remove a specific product
- `DELETE /remove/products/all`: Remove all products

### Orders

- `POST /ingest/orderlines`: Ingest order line data for recommendations
- `DELETE /remove/order/{order_id}`: Remove a specific order
- `DELETE /remove/orders/all`: Remove all orders
- `DELETE /remove/orders/user/{user_id}`: Remove all orders for a specific user

### Recommendations

- `POST /recommend/content/{product_id}`: Get content-based recommendations
- `POST /recommend/collaborative/{user_id}`: Get collaborative filtering recommendations
- `POST /recommend/hybrid/{user_id}`: Get hybrid recommendations combining multiple strategies

### Search

- `POST /search`: Main search endpoint with combined keyword and vector search
- `POST /autosuggest`: Lightweight search for autocomplete functionality
- `POST /query-explain`: Debug endpoint to explain search behavior
- `POST /feedback`: Log user feedback for future improvements

### Utility

- `GET /health`: Health check endpoint

## API Documentation

Detailed API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Local Development

For local development without Docker:

1. Create a virtual environment
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application
   ```bash
   cd app
   uvicorn main:app --reload
   ```

## Testing

Included in the project is a comprehensive test script `test_endpoints.py` that validates all functionality:

```bash
# Run all tests
python test_endpoints.py
```

You can also use the Swagger UI or curl for manual testing:

```bash
# Health check
curl -X GET http://localhost:8000/health

# Ingest a product (requires API key)
curl -X POST http://localhost:8000/ingest/products \
  -H "Content-Type: application/json" \
  -H "x-apikey: your_default_api_key" \
  -d '[{"id":"prod1","title":"Baby Shoes","description":"Comfortable shoes for babies","brand":"BabySteps","priceOriginal":299.99,"priceCurrent":249.99,"isOnSale":true,"ageFrom":1,"ageTo":3,"ageBucket":"1 to 3 years","color":"red","seasons":["winter","spring"],"productType":"main","seasonRelevancyFactor":0.8,"stockLevel":45}]'
```

## Implementation Status

- ✅ Vector search with MongoDB Atlas Search (knnBeta)
- ✅ Faceted search results for e-commerce applications
- ✅ Local embedding generation optimized for Norwegian and Swedish
- ✅ Order data ingestion and naive recommender system
- ✅ API key authorization for all secured endpoints
- ✅ Comprehensive data management functionality
- ✅ Environment-aware deployment with Docker
- ✅ Complete test suite
- ✅ Batch processing for large datasets
- ✅ Robust data transformation pipeline
- ✅ Validation framework for data integrity
- ✅ Comprehensive implementation documentation

## Data Processing Pipeline

The project includes a robust data processing pipeline for handling large datasets:

### 1. Data Transformation

Our transformation script (`scripts/data_processing/transform_data.py`) efficiently converts products from source format to the API schema:

```bash
python scripts/data_processing/transform_data.py \
  --input "path/to/source/data.json" \
  --output "transformed_data.json" \
  --batch-size 200
```

Features:

- Memory-efficient batch processing
- Error handling with appropriate fallbacks
- Field normalization for multilingual content
- Detailed logging for each transformation step

### 2. Data Validation

The validation script (`scripts/data_processing/validate_data.py`) ensures data integrity:

```bash
python scripts/data_processing/validate_data.py \
  --input "transformed_data.json" \
  --report "validation_report.json"
```

Features:

- Schema validation against API requirements
- Field coverage statistics
- Detailed validation reporting

### 3. Data Ingestion

The ingestion script (`scripts/data_processing/ingest_data.py`) loads data into MongoDB:

```bash
python scripts/data_processing/ingest_data.py \
  --input "transformed_data.json" \
  --api-url "http://localhost:8000" \
  --api-key "your-api-key" \
  --batch-size 100
```

Features:

- Configurable batch sizes for efficient loading
- Retry logic for failed ingestion attempts
- Progress tracking during ingestion

### 4. Search Testing

The testing script (`scripts/data_processing/test_search.py`) validates search functionality:

```bash
# Online mode (with API)
python scripts/data_processing/test_search.py \
  --api-url "http://localhost:8000" \
  --api-key "your-api-key" \
  --output "search_results.json"

# Offline mode (without API)
python scripts/data_processing/test_search.py \
  --offline-mode \
  --input "transformed_data.json" \
  --output "search_results.json"
```

Features:

- Support for both online and offline testing
- Multiple query types: keyword, brand, category, etc.
- Detailed search result analysis

## Test Results

Our implementation has been thoroughly tested with the following results:

### Data Processing Tests

| Test | Status | Notes |
|------|--------|-------|
| Data Transformation | ✅ Success | Processed 1,000 products with batch processing |
| Data Validation | ✅ Success | All 1,000 products passed schema validation |
| Field Coverage | ✅ Success | 100% coverage for required fields |
| Error Handling | ✅ Success | Graceful handling of data inconsistencies |

### Search Tests

| Query Type | Results | Top Result |
|------------|---------|------------|
| Keyword search | 3 | Aktivitetspakke, Solar System glow in the dark |
| Brand search | 9 | Gunghäst Vera AIDEN |
| Book search | 10 | Barnebok – Bluey Sommerfugler |
| Seasonal search | 4 | Summertime |
| Age-specific search | 10 | Cornhole Set |

## Documentation

The project includes comprehensive documentation:

- **Implementation Guide**: `docs/MongoDB_Atlas_Search_Test_Report_and_Implementation_Guide.md`
  A complete guide covering system architecture, configuration, deployment, and maintenance

- **Requirements and Progress**: `docs/Project_Requirements_and_Progress.md`
  Tracks all client requirements and implementation progress

- **Implementation Report**: `docs/Implementation_Report.md`
  Provides details on implementation decisions and technical approach

- **Data Processing Documentation**: `docs/data_processing/`
  Detailed guides for each step of the data processing pipeline

## License

MIT
