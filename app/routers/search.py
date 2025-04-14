from fastapi import APIRouter, HTTPException, status, Body, Request
from fastapi import APIRouter, HTTPException, status, Body, Request
from typing import List, Dict, Any, Optional
import json
import time

from models.product import ProductSearchQuery, AutosuggestQuery, SearchResult, FacetResult
from models.order import RecommendationQuery
from database.mongodb import get_product_collection
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
