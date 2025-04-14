# MongoDB Atlas Search API Endpoints Documentation

This document provides a comprehensive guide to all API endpoints in our MongoDB Atlas Search and Recommendation system.

## Authentication

All API endpoints (except `/health`) require API key authentication using the `x-apikey` header.

```
x-apikey: your_api_key
```

## Product Management Endpoints

### POST /ingestProducts

Accepts product data, preprocesses it (including embedding generation), and stores it in MongoDB.

**Request:**
```json
[
  {
    "id": "prod123",
    "title": "Baby Winter Shoes Blue",
    "description": "Comfortable winter shoes for babies, water resistant and warm",
    "brand": "BrandName",
    "imageThumbnailUrl": "https://example.com/image.jpg",
    "priceOriginal": 199.99,
    "priceCurrent": 149.99,
    "isOnSale": true,
    "ageFrom": 0,
    "ageTo": 1,
    "ageBucket": "0 to 1 years",
    "color": "blue",
    "seasons": ["winter"],
    "productType": "main",
    "seasonRelevancyFactor": 0.9,
    "stockLevel": 45
  }
]
```

**Response (201 Created):**
```json
["prod123"]
```

### GET /doc/{product_id}

Retrieves a complete product document by ID.

**Response (200 OK):**
```json
{
  "id": "prod123",
  "title": "Baby Winter Shoes Blue",
  "description": "Comfortable winter shoes for babies, water resistant and warm",
  "brand": "BrandName",
  "imageThumbnailUrl": "https://example.com/image.jpg",
  "priceOriginal": 199.99,
  "priceCurrent": 149.99,
  "isOnSale": true,
  "ageFrom": 0,
  "ageTo": 1,
  "ageBucket": "0 to 1 years",
  "color": "blue",
  "seasons": ["winter"],
  "productType": "main",
  "seasonRelevancyFactor": 0.9,
  "stockLevel": 45
}
```

### DELETE /remove/product/{product_id}

Removes a specific product by ID.

**Response (204 No Content)**

### DELETE /remove/products/all

Removes all products from the database.

**Response (204 No Content)**

## Order Management Endpoints

### POST /ingestOrderline

Accepts orderline data for relevancy/similarity search and recommendations.

**Request:**
```json
{
  "orderNr": "ORD-12345",
  "productNr": "prod123",
  "customerNr": "cust456",
  "seasonName": "winter",
  "dateTime": "2023-12-15T14:30:00"
}
```

**Response (201 Created):**
```json
{
  "status": "success",
  "orderNr": "ORD-12345",
  "productNr": "prod123"
}
```

## Search Endpoints

### POST /search

Performs a comprehensive search with keyword matching, vector search, and facet filters.

**Request:**
```json
{
  "query": "baby winter shoes",
  "filters": {
    "color": "blue",
    "brand": "BrandName"
  },
  "limit": 20,
  "offset": 0
}
```

**Response (200 OK):**
```json
{
  "products": [
    {
      "id": "prod123",
      "title": "Baby Winter Shoes Blue",
      "description": "Comfortable winter shoes for babies, water resistant and warm",
      "brand": "BrandName",
      "priceOriginal": 199.99,
      "priceCurrent": 149.99,
      "isOnSale": true,
      "score": 0.95
    }
  ],
  "total": 1,
  "facets": {
    "brand": [
      {"value": "BrandName", "count": 1}
    ],
    "color": [
      {"value": "blue", "count": 1}
    ],
    "ageBucket": [
      {"value": "0 to 1 years", "count": 1}
    ]
  }
}
```

### POST /autosuggest

Lightweight search optimized for prefix or partial matches to provide autocomplete suggestions.

**Request:**
```json
{
  "prefix": "ba",
  "limit": 5
}
```

**Response (200 OK):**
```json
[
  {"id": "prod123", "title": "Baby Winter Shoes Blue", "brand": "BrandName"},
  {"id": "prod124", "title": "Baby Summer Hat", "brand": "SunCare"}
]
```

### POST /similar/{product_id}

Finds similar products based on content and/or co-purchase history.

**Request:**
```json
{
  "productId": "prod123",
  "limit": 5
}
```

**Response (200 OK):**
```json
[
  {
    "id": "prod789",
    "title": "Baby Winter Socks Blue",
    "brand": "BrandName",
    "priceCurrent": 69.99,
    "similarity": 0.85
  }
]
```

### POST /query-explain

Debug endpoint to show how query was interpreted (embeddings, terms, etc.).

**Request:**
```json
{
  "query": "baby winter shoes",
  "filters": {
    "color": "blue"
  }
}
```

**Response (200 OK):**
```json
{
  "query_text": "baby winter shoes",
  "query_tokens": ["baby", "winter", "shoes"],
  "embedding_dimensions": 384,
  "embedding_sample": [0.12, 0.34, 0.56, "..."],
  "filters_applied": {
    "color": "blue"
  },
  "search_strategy": "Combined vector (knnBeta) and keyword search",
  "cache_info": {
    "search_cache": {"hits": 120, "misses": 45},
    "product_cache": {"hits": 310, "misses": 92},
    "recommendations_cache": {"hits": 201, "misses": 77}
  }
}
```

### POST /feedback

Log user actions for learning-to-rank or query tuning.

**Request:**
```json
{
  "query": "baby shoes",
  "clicked_product_id": "prod123",
  "results_shown": ["prod123", "prod456", "prod789"],
  "user_id": "user123",
  "session_id": "sess456"
}
```

**Response (200 OK):**
```json
{
  "status": "feedback received"
}
```

## Naive Recommender Endpoints

### POST /naive-recommender/compute-product-pairs

Triggers background pre-computation of product pairs for recommendations.

**Response (202 Accepted):**
```json
{
  "task_id": "task123",
  "status": "processing"
}
```

### GET /naive-recommender/product-pairs-status

Checks the status of product pairs computation.

**Response (200 OK):**
```json
{
  "status": "completed",
  "last_computed": "2023-12-15T14:30:00",
  "pair_count": 1250
}
```

### GET /naive-recommender/user/{user_id}/collaborative

Get collaborative filtering recommendations based on user purchase history.

**Response (200 OK):**
```json
[
  {
    "id": "prod456",
    "score": 0.87,
    "product": {
      "id": "prod456",
      "title": "Baby Winter Hat Blue",
      "brand": "BrandName",
      "priceCurrent": 79.99
    }
  }
]
```

### GET /naive-recommender/product/{product_id}/content-based

Get content-based recommendations based on product attributes.

**Response (200 OK):**
```json
[
  {
    "id": "prod789",
    "score": 0.92,
    "product": {
      "id": "prod789",
      "title": "Baby Winter Socks Blue",
      "brand": "BrandName",
      "priceCurrent": 69.99
    }
  }
]
```

### GET /naive-recommender/user/{user_id}/hybrid

Get hybrid recommendations combining collaborative and content-based approaches.

**Response (200 OK):**
```json
[
  {
    "id": "prod456",
    "score": 0.94,
    "product": {
      "id": "prod456",
      "title": "Baby Winter Hat Blue",
      "brand": "BrandName",
      "priceCurrent": 79.99
    }
  }
]
```

### GET /naive-recommender/product/{product_id}/frequently-bought-together

Get products frequently purchased together with the specified product.

**Response (200 OK):**
```json
[
  {
    "id": "prod456",
    "score": 0.95,
    "product": {
      "id": "prod456",
      "title": "Baby Winter Hat Blue",
      "brand": "BrandName",
      "priceCurrent": 79.99
    }
  }
]
```

## System Endpoints

### GET /health

Health check endpoint for monitoring system status. This endpoint does NOT require API key authentication.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": 1673845200,
  "version": "1.0.0",
  "database_connection": "ok",
  "services": {
    "mongodb": {
      "status": "healthy",
      "collections": {
        "products": {
          "count": 1000,
          "size_mb": 5.2
        },
        "orderlines": {
          "count": 5000,
          "size_mb": 3.1
        },
        "product_pairs": {
          "count": 1250,
          "size_mb": 0.8
        }
      }
    }
  },
  "response_time_ms": 5.2
}
```

### GET /api-stats

API usage statistics and metrics. Requires API key authentication.

**Response (200 OK):**
```json
{
  "search_metrics": {
    "average_processing_time": 35.2,
    "popular_queries": [
      {"query": "baby shoes", "count": 25},
      {"query": "winter clothes", "count": 18}
    ],
    "recent_searches": [
      {"query": "baby toys", "timestamp": "2023-12-15T14:30:00"},
      {"query": "baby clothes", "timestamp": "2023-12-15T14:28:30"}
    ]
  }
}
```

## Error Responses

### 401 Unauthorized
```json
{
  "detail": "Invalid or missing API key"
}
```

### 404 Not Found
```json
{
  "detail": "Product with ID prod999 not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error occurred"
}
```
