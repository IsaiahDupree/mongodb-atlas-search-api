"""
A simplified search implementation for local testing that doesn't depend on 
MongoDB Atlas Search features. This module is used when TEST_MODE is enabled.
"""
from fastapi import APIRouter, HTTPException, status, Body, Request, Depends
from typing import List, Dict, Any, Optional
import json
import time
import re
import random

from models.product import ProductSearchQuery, AutosuggestQuery, SearchResult, FacetResult
from database.mongodb import get_product_collection
from services.embedding import embedding_service
from services.cache import search_cache
from dependencies import get_api_key

router = APIRouter(
    prefix="/search",
    tags=["Search"],
    dependencies=[Depends(get_api_key)]
)

@router.post("", response_model=SearchResult)
async def search_products(request: Request, query: ProductSearchQuery = Body(...)):
    """
    Simplified search endpoint for local testing that doesn't use Atlas Search features.
    """
    start_time = time.time()
    
    # Check cache first
    cache_key = f"search:{query.query}:{query.limit}:{query.offset}:{json.dumps(query.filters or {})}"
    cached_result = search_cache.get(cache_key)
    if cached_result:
        request.state.processing_time = 0.001  # Negligible time for cache hit
        return SearchResult(**cached_result)
    
    collection = await get_product_collection()
    
    # Build a simple filter for MongoDB find() operation
    mongo_filter = {}
    
    # Add text search with regex
    if query.query:
        # Case-insensitive regex search
        text_regex = re.compile(f".*{re.escape(query.query)}.*", re.IGNORECASE)
        mongo_filter["$or"] = [
            {"title": {"$regex": text_regex}},
            {"description": {"$regex": text_regex}},
            {"brand": {"$regex": text_regex}}
        ]
    
    # Add user filters
    if query.filters:
        for key, value in query.filters.items():
            if key not in mongo_filter:
                mongo_filter[key] = value
    
    # Get total count for pagination
    total_count = await collection.count_documents(mongo_filter)
    
    # Execute find with pagination
    cursor = collection.find(
        mongo_filter, 
        skip=query.offset,
        limit=query.limit
    )
    
    # Process results
    products = []
    async for doc in cursor:
        # Convert MongoDB _id to string and remove from response
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        
        # Add a random score since we can't use Atlas Search scoring
        doc["score"] = random.uniform(0.5, 1.0)
        
        # Add to results
        products.append(doc)
    
    # Generate facets by analyzing all matching documents
    # This is not efficient for large collections but works for testing
    facets = []
    facet_fields = ["brand", "color", "productType", "isOnSale", "seasons"]
    
    if total_count > 0 and total_count < 1000:  # Only calculate facets for reasonable result sets
        for field in facet_fields:
            facet_cursor = collection.aggregate([
                {"$match": mongo_filter},
                {"$group": {"_id": f"${field}", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 10}
            ])
            
            values = []
            async for facet_value in facet_cursor:
                if facet_value["_id"] is not None:
                    values.append({
                        "value": facet_value["_id"],
                        "count": facet_value["count"]
                    })
            
            if values:
                facets.append({
                    "name": field,
                    "values": values
                })
    
    # Calculate processing time
    processing_time = time.time() - start_time
    
    # Create response
    response = SearchResult(
        query=query.query,
        products=products,
        facets=facets,
        total=total_count
    )
    
    # Cache the result
    search_cache.set(cache_key, response.dict())
    
    # Record processing time for monitoring
    request.state.processing_time = processing_time
    
    return response

@router.post("/autosuggest", response_model=List[Dict[str, Any]])
async def autosuggest(request: Request, query: AutosuggestQuery = Body(...)):
    """
    Simplified autosuggest endpoint for local testing
    """
    # Check cache first
    cache_key = f"autosuggest:{query.prefix}:{query.limit}"
    cached_result = search_cache.get(cache_key)
    if cached_result:
        return cached_result
    
    start_time = time.time()
    collection = await get_product_collection()
    
    # Simple prefix match with regex
    regex = re.compile(f"^{re.escape(query.prefix)}.*", re.IGNORECASE)
    cursor = collection.find(
        {"title": {"$regex": regex}},
        {"_id": 0, "id": 1, "title": 1, "brand": 1}
    ).limit(query.limit)
    
    results = []
    async for doc in cursor:
        results.append(doc)
    
    # Cache results
    search_cache.set(cache_key, results)
    
    # Record processing time
    processing_time = time.time() - start_time
    request.state.processing_time = processing_time
    
    return results

@router.post("/query-explain", response_model=Dict[str, Any])
async def query_explain(request: Request, query: ProductSearchQuery = Body(...)):
    """
    Debug endpoint to explain how the local search works
    """
    # Generate embedding (for test mode this will be random)
    query_embedding = embedding_service.generate_embedding(query.query)
    
    # Truncate embedding for display purposes
    truncated_embedding = query_embedding[:5] + ["..."] if len(query_embedding) > 5 else query_embedding
    
    # Build explanation for local testing
    explanation = {
        "query_text": query.query,
        "query_tokens": query.query.split(),
        "search_type": "Local testing search (regex-based)",
        "test_mode": True,
        "embedding_sample": truncated_embedding,
        "filters_applied": query.filters,
        "note": "This is a simplified search implementation for local testing."
    }
    
    # Add cache info
    explanation["cache_info"] = {
        "search_cache": search_cache.get_stats()
    }
    
    return explanation

@router.post("/feedback")
async def log_feedback(feedback: Dict[str, Any] = Body(...)):
    """
    Placeholder for feedback logging in test mode
    """
    print(f"[TEST MODE] Search feedback received: {json.dumps(feedback)}")
    
    return {"status": "feedback received (test mode)"}
