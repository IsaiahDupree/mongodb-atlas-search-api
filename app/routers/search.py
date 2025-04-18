from fastapi import APIRouter, HTTPException, status, Body, Request
from fastapi import APIRouter, HTTPException, status, Body, Request
from typing import List, Dict, Any, Optional
import json
import time
import asyncio

from models.product import (
    ProductSearchQuery, AutosuggestQuery, SearchResult, FacetResult,
    ConsolidatedSearchRequest, ConsolidatedSearchResponse, 
    CategoryResult, BrandResult
)
from models.order import RecommendationQuery
from database.mongodb import get_product_collection, get_database
from services.embedding import embedding_service
from services.cache import search_cache, product_cache, recommendations_cache
from services.monitoring import SearchMetrics

router = APIRouter()

@router.post("/search", response_model=SearchResult)
async def search_products(request: Request, query: ProductSearchQuery = Body(...)):
    """
    Main search endpoint that combines keyword and vector search to return ranked results.
    Supports faceted search results for filtering.
    """
    collection = await get_product_collection()
    
    # Generate embedding for the query
    query_embedding = embedding_service.generate_embedding(query.query)
    
    # Build MongoDB Atlas search pipeline
    # This includes vector search combined with keyword matching
    pipeline = []
    
    # Create a $search stage for MongoDB Atlas Search
    search_stage = {
        "$search": {
            "index": "product_search",  # This would be the name of your Atlas Search index
            "compound": {
                "should": [
                    # Vector search on title embeddings
                    {
                        "knnBeta": {
                            "vector": query_embedding,
                            "path": "title_embedding",
                            "k": 100,
                            "score": {"boost": {"value": 1.5}}  # Higher weight on title matches
                        }
                    },
                    # Vector search on description embeddings
                    {
                        "knnBeta": {
                            "vector": query_embedding,
                            "path": "description_embedding",
                            "k": 100,
                            "score": {"boost": {"value": 1.0}}
                        }
                    },
                    # Text search for exact and close matches
                    {
                        "text": {
                            "query": query.query,
                            "path": ["title", "description", "brand"],
                            "score": {"boost": {"value": 2.0}}  # Higher weight on text matches
                        }
                    }
                ]
            },
            "returnStoredSource": True,
            "facets": {
                # Define facets for filtering results
                "brand": {"type": "string", "path": "brand"},
                "color": {"type": "string", "path": "color"},
                "ageBucket": {"type": "string", "path": "ageBucket"},
                "isOnSale": {"type": "boolean", "path": "isOnSale"},
                "seasons": {"type": "string", "path": "seasons"}
            }
        }
    }
    
    pipeline.append(search_stage)
    
    # Add filter stage if filters are provided
    if query.filters:
        filter_conditions = {}
        for key, value in query.filters.items():
            filter_conditions[key] = value
        
        pipeline.append({"$match": filter_conditions})
    
    # Add pagination
    pipeline.append({"$skip": query.offset})
    pipeline.append({"$limit": query.limit})
    
    # Execute the search pipeline
    search_results = []
    facets = []
    total_count = 0
    
    try:
        # Extract facets and results from the search response
        cursor = collection.aggregate(pipeline)
        
        # Process results
        async for doc in cursor:
            # Remove MongoDB _id and embedding vectors from response
            if "_id" in doc:
                del doc["_id"]
            if "title_embedding" in doc:
                del doc["title_embedding"]
            if "description_embedding" in doc:
                del doc["description_embedding"]
            
            search_results.append(doc)
            
        # Since Atlas Search facets are not easily simulated in this example,
        # we'll add a separate aggregation to get facet counts
        facet_pipeline = []
        for facet_field in ["brand", "color", "ageBucket", "isOnSale", "seasons"]:
            facet_group = {
                f"{facet_field}_values": [
                    {"$unwind": {"path": f"${facet_field}", "preserveNullAndEmptyArrays": True}},
                    {"$group": {"_id": f"${facet_field}", "count": {"$sum": 1}}},
                    {"$sort": {"count": -1}},
                    {"$limit": 10}
                ]
            }
            facet_pipeline.append({"$facet": facet_group})
        
        # Get facet counts
        facet_results = await collection.aggregate(facet_pipeline).to_list(1)
        if facet_results:
            facet_result = facet_results[0]
            for field, values in facet_result.items():
                # Strip _values suffix from field name
                field_name = field.replace("_values", "")
                facet = FacetResult(field=field_name, values=[{"value": item["_id"], "count": item["count"]} for item in values])
                facets.append(facet)
        
        # Get total count
        total_count = len(search_results)
        
    except Exception as e:
        print(f"Search error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )
    
    # Calculate processing time for metrics
    processing_time = time.time() - start_time
    
    # Create search response
    response = SearchResult(
        total=total_count,
        products=search_results,
        facets=facets,
        query_explanation={"query_embedding_length": len(query_embedding), "filters": query.filters}
    )
    
    # Record search metrics
    SearchMetrics.record_search(
        query=query.query, 
        filters=query.filters,
        results_count=total_count,
        processing_time=processing_time
    )
    
    # Cache the result
    search_cache.set(cache_key, response.dict())
    
    request.state.processing_time = processing_time
    
    return response

@router.post("/autosuggest", response_model=List[Dict[str, Any]])
async def autosuggest(request: Request, query: AutosuggestQuery = Body(...)):
    """
    Lighter variant of search, optimized for prefix or partial matches.
    Provides fast autocomplete suggestions.
    """
    collection = await get_product_collection()
    
    # Build autocomplete query
    pipeline = [
        {
            "$search": {
                "index": "product_search",  # Atlas Search index
                "autocomplete": {
                    "query": query.prefix,
                    "path": "title",  # Search in title field
                    "fuzzy": {
                        "maxEdits": 1  # Allow 1 typo
                    }
                }
            }
        },
        # Project only the needed fields
        {
            "$project": {
                "_id": 0,
                "id": 1,
                "title": 1,
                "brand": 1
            }
        },
        # Limit results
        {
            "$limit": query.limit
        }
    ]
    
    # Check cache first
    cache_key = {"prefix": query.prefix, "limit": query.limit}
    cached_result = search_cache.get(cache_key)
    
    if cached_result:
        return cached_result
    
    # Start timing for performance monitoring
    start_time = time.time()
    
    # Execute query
    try:
        results = await collection.aggregate(pipeline).to_list(query.limit)
        
        # Cache the result
        search_cache.set(cache_key, results)
        
        # Record processing time
        processing_time = time.time() - start_time
        request.state.processing_time = processing_time
        
        return results
    except Exception as e:
        print(f"Autosuggest error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Autosuggest failed: {str(e)}"
        )

@router.post("/query-explain", response_model=Dict[str, Any])
async def query_explain(request: Request, query: ProductSearchQuery = Body(...)):
    """
    Debug endpoint to show how query was interpreted (embeddings, terms used, etc.)
    """
    # Generate embedding for the query
    query_embedding = embedding_service.generate_embedding(query.query)
    
    # Truncate embedding for display purposes
    truncated_embedding = query_embedding[:10] + ["..."] if len(query_embedding) > 10 else query_embedding
    
    # Build explanation
    explanation = {
        "query_text": query.query,
        "query_tokens": query.query.split(),
        "embedding_dimensions": len(query_embedding),
        "embedding_sample": truncated_embedding,
        "filters_applied": query.filters,
        "search_strategy": "Combined vector (knnBeta) and keyword search"
    }
    
    # Get cache stats for the explanation
    cache_stats = {
        "search_cache": search_cache.get_stats(),
        "product_cache": product_cache.get_stats(),
        "recommendations_cache": recommendations_cache.get_stats()
    }
    
    # Add cache info to explanation
    explanation["cache_info"] = cache_stats
    
    return explanation

@router.post("/feedback")
async def log_feedback(feedback: Dict[str, Any] = Body(...)):
    """
    Log user actions for learning-to-rank or query tuning
    """
    # Placeholder for feedback logging
    # In a real system, this would store feedback for future ML training
    
    # Example of expected feedback format:
    # {
    #   "query": "baby shoes",
    #   "clicked_product_id": "prod1",
    #   "results_shown": ["prod1", "prod2", "prod3"],
    #   "user_id": "anonymous-123",
    #   "session_id": "abc-xyz-123"
    # }
    
    # For now, just log to console
    print(f"Search feedback received: {json.dumps(feedback)}")
    
    return {"status": "feedback received"}


@router.post("/consolidated-search", response_model=ConsolidatedSearchResponse)
async def consolidated_search(request: Request, query: ConsolidatedSearchRequest = Body(...)):
    """
    Consolidated search endpoint that returns categories, brands, and products in a single response.
    This is ideal for unified search experiences where different result types are displayed together.
    
    - Categories: Exact substring matches
    - Brands: Exact substring matches
    - Products: Combination of exact, ngram, and vector search
    """
    # Validate minimum query length
    if len(query.query) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query must be at least 3 characters long"
        )
    
    # Check cache first
    cache_key = query.dict()
    cached_result = search_cache.get(cache_key)
    if cached_result:
        return cached_result
    
    # Start timing for performance monitoring
    start_time = time.time()
    
    # Get database collection
    collection = await get_product_collection()
    db = await get_database()
    
    # Generate embeddings for vector search if needed (for multi-word queries)
    embeddings = None
    if query.includeVectorSearch and " " in query.query:
        embeddings = embedding_service.generate_embedding(query.query)
    
    # Execute parallel searches for each result type
    categories_task = search_categories(db, collection, query.query, query.maxCategories)
    brands_task = search_brands(db, collection, query.query, query.maxBrands)
    products_task = search_products_consolidated(
        db, 
        collection, 
        query.query, 
        embeddings, 
        query.maxProducts,
        query.includeVectorSearch
    )
    
    # Wait for all searches to complete concurrently
    categories, brands, products = await asyncio.gather(
        categories_task, 
        brands_task, 
        products_task
    )
    
    # Calculate processing time
    processing_time = (time.time() - start_time) * 1000
    
    # Compile response
    response = ConsolidatedSearchResponse(
        categories=categories,
        brands=brands,
        products=products,
        metadata={
            "totalResults": len(categories) + len(brands) + len(products),
            "processingTimeMs": processing_time,
            "query": query.query
        }
    )
    
    # Cache the result
    search_cache.set(cache_key, response.dict())
    
    # Record processing time for monitoring
    request.state.processing_time = processing_time
    
    return response


async def search_categories(db, collection, query_text: str, max_results: int) -> List[CategoryResult]:
    """
    Search for categories with exact substring matches
    """
    # Extract unique categories from the product collection
    # MongoDB doesn't have a built-in categories collection, so we need to query products
    # and extract unique categories
    try:
        # This is a simplified approach - in a real application, you might have a separate categories collection
        pipeline = [
            # Find products where category name or slug contains the query (case insensitive)
            {
                "$match": {
                    "$or": [
                        {"categories.name": {"$regex": query_text, "$options": "i"}},
                        {"categories.slug": {"$regex": query_text, "$options": "i"}}
                    ]
                }
            },
            # Unwind categories array to work with individual categories
            {"$unwind": "$categories"},
            # Filter to only include categories that match the query
            {
                "$match": {
                    "$or": [
                        {"categories.name": {"$regex": query_text, "$options": "i"}},
                        {"categories.slug": {"$regex": query_text, "$options": "i"}}
                    ]
                }
            },
            # Group by category id to get unique categories and count products
            {
                "$group": {
                    "_id": "$categories.id",
                    "name": {"$first": "$categories.name"},
                    "slug": {"$first": "$categories.slug"},
                    "productCount": {"$sum": 1}
                }
            },
            # Sort by product count (most popular categories first)
            {"$sort": {"productCount": -1}},
            # Limit to max_results
            {"$limit": max_results},
            # Project to final format
            {
                "$project": {
                    "_id": 0,
                    "id": "$_id",
                    "name": 1,
                    "slug": 1,
                    "productCount": 1
                }
            }
        ]
        
        # Execute the pipeline
        cursor = collection.aggregate(pipeline)
        results = await cursor.to_list(length=max_results)
        
        # Convert to CategoryResult objects
        return [CategoryResult(**result) for result in results]
    except Exception as e:
        print(f"Error searching categories: {str(e)}")
        # Return empty list on error rather than failing the whole response
        return []


async def search_brands(db, collection, query_text: str, max_results: int) -> List[BrandResult]:
    """
    Search for brands with exact substring matches
    """
    try:
        # Find brands that match the query
        pipeline = [
            # Match products where brand contains the query (case insensitive)
            {"$match": {"brand": {"$regex": query_text, "$options": "i"}}},
            # Group by brand to get unique brands and count products
            {
                "$group": {
                    "_id": "$brand",
                    "productCount": {"$sum": 1}
                }
            },
            # Sort by product count (most popular brands first)
            {"$sort": {"productCount": -1}},
            # Limit to max_results
            {"$limit": max_results},
            # Project to final format
            {
                "$project": {
                    "_id": 0,
                    "id": "$_id",  # Use brand name as ID
                    "name": "$_id",
                    "productCount": 1
                }
            }
        ]
        
        # Execute the pipeline
        cursor = collection.aggregate(pipeline)
        results = await cursor.to_list(length=max_results)
        
        # Convert to BrandResult objects
        return [BrandResult(**result) for result in results]
    except Exception as e:
        print(f"Error searching brands: {str(e)}")
        # Return empty list on error rather than failing the whole response
        return []


async def search_products_consolidated(db, collection, query_text: str, embeddings: List[float], 
                                       max_results: int, include_vector_search: bool) -> List[Dict[str, Any]]:
    """
    Search for products using multiple strategies:
    1. Exact matching
    2. Substring matching
    3. Ngram matching
    4. Vector search (if enabled and query has multiple words)
    """
    try:
        # Build MongoDB Atlas search pipeline with multiple strategies
        search_stage = {
            "$search": {
                "index": "product_search",  # Atlas Search index
                "compound": {
                    "should": [
                        # Exact match (highest boost)
                        {
                            "text": {
                                "query": query_text,
                                "path": ["title", "description", "brand"],
                                "score": {"boost": {"value": 5}}
                            }
                        },
                        # Substring/fuzzy match
                        {
                            "text": {
                                "query": query_text,
                                "path": "title",
                                "fuzzy": {"maxEdits": 1},
                                "score": {"boost": {"value": 3}}
                            }
                        },
                        # Ngram match for partial words
                        {
                            "autocomplete": {
                                "query": query_text,
                                "path": "title",
                                "tokenOrder": "any",
                                "score": {"boost": {"value": 2}}
                            }
                        }
                    ]
                }
            }
        }
        
        # Add vector search if enabled and we have embeddings
        if include_vector_search and embeddings and " " in query_text:
            vector_stage = {
                "knnBeta": {
                    "vector": embeddings,
                    "path": "title_embedding",
                    "k": 50,
                    "score": {"boost": {"value": 1}}
                }
            }
            search_stage["$search"]["compound"]["should"].append(vector_stage)
        
        # Build the full pipeline
        pipeline = [
            search_stage,
            # Add a stage to determine match type
            {
                "$addFields": {
                    "score": {"$meta": "searchScore"},
                    "matchType": {
                        "$cond": [
                            # Check if title contains exact query (case insensitive)
                            {"$regexMatch": {"input": "$title", "regex": query_text, "options": "i"}},
                            "exact",
                            # Check score to determine if it's ngram or vector match
                            {
                                "$cond": [
                                    {"$gt": [{"$meta": "searchScore"}, 1.5]},
                                    "ngram",
                                    "vector"
                                ]
                            }
                        ]
                    }
                }
            },
            # Limit to max_results
            {"$limit": max_results},
            # Project only needed fields
            {
                "$project": {
                    "_id": 0,
                    "id": 1,
                    "title": 1,
                    "description": 1,
                    "brand": 1,
                    "imageThumbnailUrl": 1,
                    "priceOriginal": 1,
                    "priceCurrent": 1,
                    "isOnSale": 1,
                    "score": 1,
                    "matchType": 1
                }
            }
        ]
        
        # Execute the pipeline
        cursor = collection.aggregate(pipeline)
        results = await cursor.to_list(length=max_results)
        
        return results
    except Exception as e:
        print(f"Error searching products: {str(e)}")
        # Return empty list on error rather than failing the whole response
        return []
