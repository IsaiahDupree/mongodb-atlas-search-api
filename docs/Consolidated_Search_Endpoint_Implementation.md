# Consolidated Search Endpoint Implementation

**Date:** April 18, 2025  
**Version:** 1.0

## Overview

This document outlines the implementation approach for a new consolidated search endpoint that returns categories, brands, and products in a single response. This endpoint will provide a richer search experience by allowing the UI to display different types of results simultaneously.

## Requirements

The consolidated search endpoint will:

1. Accept search queries (minimum 3 characters)
2. Return a JSON response containing three arrays:
   - Categories with exact substring matches
   - Brands with exact substring matches
   - Products matching the query through various methods (substring, ngram, vector search)
3. Support configuration for maximum results per section
4. Handle partial word searches as well as complete words and phrases
5. Support multilingual content (Norwegian and Swedish)

## API Specification

### Endpoint

```http
POST /consolidated-search
```

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | Search query (minimum 3 characters) |
| `maxCategories` | integer | No | Maximum number of category results (default: 10) |
| `maxBrands` | integer | No | Maximum number of brand results (default: 10) |
| `maxProducts` | integer | No | Maximum number of product results (default: 20) |
| `includeVectorSearch` | boolean | No | Whether to include vector search for products (default: true) |

### Request Example


```json
{
  "query": "metaldetector",
  "maxCategories": 5,
  "maxBrands": 5,
  "maxProducts": 15,
  "includeVectorSearch": true
}
```


### Response Format


```json
{
  "categories": [
    {
      "id": "string",
      "name": "string",
      "slug": "string",
      "productCount": 0
    }
  ],
  "brands": [
    {
      "id": "string",
      "name": "string",
      "productCount": 0
    }
  ],
  "products": [
    {
      "id": "string",
      "title": "string",
      "description": "string",
      "brand": "string",
      "imageThumbnailUrl": "string",
      "priceOriginal": 0,
      "priceCurrent": 0,
      "isOnSale": true,
      "score": 0,
      "matchType": "exact|ngram|vector" 
    }
  ],
  "metadata": {
    "totalResults": 0,
    "processingTimeMs": 0
  }
}
```


## Search Strategy

### Category Search

Categories will be searched using exact substring matching:

1. Convert query to lowercase
2. Search for substring matches in category name and slug
3. Rank exact matches higher than partial matches
4. Sort by relevance score and limit to maxCategories

### Brand Search

Brands will be searched using exact substring matching:

1. Convert query to lowercase
2. Search for substring matches in brand name
3. Rank exact matches higher than partial matches
4. Sort by relevance score and limit to maxBrands

### Product Search

Products will be searched using a multi-strategy approach:


1. **Exact Match**: Find products with exact matches in title, description, or brand
2. **Substring Match**: Find products with partial substring matches
3. **Ngram Match**: Use ngram tokenization to handle partial words
4. **Vector Search**: For multi-word queries, use vector embeddings for semantic matching

The product search algorithm will:

1. Execute all applicable search strategies
2. Combine and deduplicate results
3. Score and rank based on match quality
4. Limit to maxProducts with highest relevance

## MongoDB Atlas Configuration

### Creating Text and Vector Indexes

To support the combined search, we'll configure MongoDB Atlas with:

1. **Text Index for String Matching**:
   ```json
   {
     "mappings": {
       "dynamic": true,
       "fields": {
         "title": {
           "type": "string",
           "analyzer": "lucene.standard"
         },
         "brand": {
           "type": "string",
           "analyzer": "lucene.standard"
         },
         "categories.name": {
           "type": "string",
           "analyzer": "lucene.standard"
         },
         "categories.slug": {
           "type": "string",
           "analyzer": "lucene.standard"
         }
       }
     }
   }
   ```

2. **Ngram Index for Partial Matching**:
   ```json
   {
     "mappings": {
       "dynamic": true,
       "fields": {
         "title": {
           "type": "string",
           "analyzer": "lucene.ngram",
           "tokenizer": {
             "type": "nGram",
             "minGram": 3,
             "maxGram": 4
           }
         }
       }
     }
   }
   ```

3. **Vector Index for Semantic Search**:
   ```json
   {
     "mappings": {
       "dynamic": true,
       "fields": {
         "title_embedding": {
           "type": "knnVector",
           "dimensions": 384,
           "similarity": "cosine"
         },
         "description_embedding": {
           "type": "knnVector",
           "dimensions": 384,
           "similarity": "cosine"
         }
       }
     }
   }
   ```

## Implementation Approach

### 1. Create MongoDB Aggregation Pipeline

For the category search:


```javascript
[
  {
    $search: {
      index: "default",
      text: {
        query: query,
        path: ["categories.name", "categories.slug"],
        fuzzy: { maxEdits: 1 }
      }
    }
  },
  { $limit: maxCategories },
  {
    $project: {
      _id: 0,
      id: "$categories.id",
      name: "$categories.name",
      slug: "$categories.slug",
      productCount: { $size: "$products" }
    }
  }
]
```


For the brand search:

```javascript
[
  {
    $search: {
      index: "default",
      text: {
        query: query,
        path: "brand",
        fuzzy: { maxEdits: 1 }
      }
    }
  },
  {
    $group: {
      _id: "$brand",
      productCount: { $sum: 1 }
    }
  },
  { $limit: maxBrands },
  {
    $project: {
      _id: 0,
      id: "$_id",
      name: "$_id",
      productCount: 1
    }
  }
]
```

For the product search (combined):

```javascript
[
  {
    $search: {
      "compound": {
        "should": [
          {
            "text": {
              "query": query,
              "path": ["title", "description", "brand"],
              "score": { "boost": { "value": 3 } }
            }
          },
          {
            "autocomplete": {
              "query": query,
              "path": "title",
              "tokenOrder": "sequential",
              "score": { "boost": { "value": 2 } }
            }
          },
          {
            "knnBeta": {
              "vector": queryEmbedding,
              "path": "title_embedding",
              "k": 50,
              "score": { "boost": { "value": 1 } }
            }
          }
        ]
      }
    }
  },
  { $limit: maxProducts },
  {
    $project: {
      _id: 0,
      id: 1,
      title: 1,
      description: 1,
      brand: 1,
      imageThumbnailUrl: 1,
      priceOriginal: 1,
      priceCurrent: 1,
      isOnSale: 1,
      score: { $meta: "searchScore" },
      matchType: {
        $cond: {
          if: { $regexMatch: { input: "$title", regex: query, options: "i" } },
          then: "exact",
          else: {
            $cond: {
              if: { $gt: [{ $meta: "searchScore" }, 1.5] },
              then: "ngram",
              else: "vector"
            }
          }
        }
      }
    }
  }
]
```

### 2. FastAPI Implementation

```python
@router.post("/consolidated-search")
async def consolidated_search(
    request: ConsolidatedSearchRequest,
    db: AsyncIOMotorClient = Depends(get_database)
):
    query = request.query
    
    # Validate minimum query length
    if len(query) < 3:
        raise HTTPException(
            status_code=400, 
            detail="Search query must be at least 3 characters long"
        )
    
    # Generate embeddings for vector search if needed
    embeddings = None
    if request.includeVectorSearch and " " in query:
        embeddings = await generate_embeddings(query)
    
    # Execute parallel searches
    categories_task = search_categories(db, query, request.maxCategories)
    brands_task = search_brands(db, query, request.maxBrands)
    products_task = search_products(
        db, 
        query, 
        embeddings, 
        request.maxProducts,
        request.includeVectorSearch
    )
    
    # Wait for all searches to complete
    start_time = time.time()
    categories, brands, products = await asyncio.gather(
        categories_task, 
        brands_task, 
        products_task
    )
    processing_time = (time.time() - start_time) * 1000
    
    # Compile response
    return {
        "categories": categories,
        "brands": brands,
        "products": products,
        "metadata": {
            "totalResults": len(categories) + len(brands) + len(products),
            "processingTimeMs": processing_time
        }
    }
```

## Test Cases

The implementation must pass the following test cases:

### Case 1: Exact Word Match

Query: "metaldetector"
- Should return category matches for "metal detectors"
- Should return brand matches for manufacturers of metal detectors
- Should return products with "metaldetector" in title, description or brand

### Case 2: Partial Word Match

Query: "met"
- Should return metal detector categories
- Should return brands containing "met"
- Should return products containing "metal", "metaldetector", etc.

### Case 3: Partial Word Test Cases


All of these searches should find "metaldetector" products:

- "met"
- "meta" 
- "metall"
- "metalde"
- "metaldetect"


### Case 4: Multi-Word Query

Query: "silver metal detector"
- Should use vector search to find semantically related products
- Should blend exact match results with vector search results

### Case 5: Ngram Tokenization 

Query: "metalde"
- Should use ngram tokenization to match "metaldetector"
- Should prioritize products with closest ngram matches

## Performance Considerations


1. **Caching**: Implement Redis caching for frequent queries
2. **Pagination**: Support pagination for larger result sets
3. **Query Performance**: Use MongoDB explain plan to optimize queries
4. **Response Size**: Limit the fields returned to minimize response size


## Next Steps


1. Implement the FastAPI endpoint as specified
2. Configure MongoDB Atlas indexes for all search types
3. Set up test suite to verify all test cases
4. Benchmark performance and optimize as needed
5. Document the API endpoint in the Swagger UI

