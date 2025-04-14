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

## License

MIT
