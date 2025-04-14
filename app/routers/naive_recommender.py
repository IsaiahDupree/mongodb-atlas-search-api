from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks, Request
from typing import List, Dict, Any, Optional

from models.product import Product
from database.mongodb import get_product_collection, db
from services.naive_recommender import NaiveRecommender
from services.cache import recommendations_cache
from dependencies import get_api_key
import time

router = APIRouter(
    prefix="/naive-recommender",
    tags=["Naive Recommender"],
    dependencies=[Depends(get_api_key)]
)

# Use lazy initialization for the recommender
_recommender_instance = None

def get_recommender():
    """Get or create the recommender instance (lazy initialization)"""
    global _recommender_instance
    if _recommender_instance is None:
        _recommender_instance = NaiveRecommender(db.db)
    return _recommender_instance

@router.post("/compute-product-pairs", status_code=status.HTTP_202_ACCEPTED)
async def compute_product_pairs(background_tasks: BackgroundTasks):
    """
    Pre-compute product pairs for recommendation (resource-intensive operation).
    This operation runs in the background.
    """
    background_tasks.add_task(get_recommender().pre_compute_product_pairs)
    return {"status": "Product pairs computation started in the background"}

@router.get("/product-pairs-status")
async def get_product_pairs_status():
    """
    Get status of product pairs computation
    """
    count = await db.db.product_pairs.count_documents({})
    return {
        "status": "Ready" if count > 0 else "Not computed",
        "product_pairs_count": count
    }

@router.get("/user/{user_id}/collaborative", response_model=List[Dict[str, Any]])
async def get_collaborative_recommendations(
    request: Request,
    user_id: str,
    limit: int = Query(10, ge=1, le=50)
):
    """
    Get personalized recommendations based on user purchase history (collaborative filtering)
    """
    # Check cache
    cache_key = f"collab_rec:{user_id}:{limit}"
    cached_result = recommendations_cache.get(cache_key)
    if cached_result:
        return cached_result
    
    # Start timing
    start_time = time.time()
    
    # Get recommendations
    recommendations = await get_recommender().get_collaborative_recommendations(user_id, limit)
    
    # Cache result
    recommendations_cache.set(cache_key, recommendations)
    
    # Record processing time
    request.state.processing_time = time.time() - start_time
    
    return recommendations

@router.get("/product/{product_id}/content-based", response_model=List[Dict[str, Any]])
async def get_content_based_recommendations(
    request: Request,
    product_id: str,
    limit: int = Query(5, ge=1, le=20)
):
    """
    Get content-based recommendations based on a product
    """
    # Check cache
    cache_key = f"content_rec:{product_id}:{limit}"
    cached_result = recommendations_cache.get(cache_key)
    if cached_result:
        return cached_result
    
    # Start timing
    start_time = time.time()
    
    # Get recommendations
    recommendations = await get_recommender().get_content_based_recommendations(product_id, limit)
    
    # Cache result
    recommendations_cache.set(cache_key, recommendations)
    
    # Record processing time
    request.state.processing_time = time.time() - start_time
    
    return recommendations

@router.get("/user/{user_id}/hybrid", response_model=List[Dict[str, Any]])
async def get_hybrid_recommendations(
    request: Request,
    user_id: str,
    limit: int = Query(10, ge=1, le=50)
):
    """
    Get hybrid recommendations combining collaborative filtering and content-based approaches
    """
    # Check cache
    cache_key = f"hybrid_rec:{user_id}:{limit}"
    cached_result = recommendations_cache.get(cache_key)
    if cached_result:
        return cached_result
    
    # Start timing
    start_time = time.time()
    
    # Get recommendations
    recommendations = await get_recommender().get_hybrid_recommendations(user_id, limit)
    
    # Cache result
    recommendations_cache.set(cache_key, recommendations)
    
    # Record processing time
    request.state.processing_time = time.time() - start_time
    
    return recommendations

@router.get("/product/{product_id}/frequently-bought-together", response_model=List[Dict[str, Any]])
async def get_frequently_bought_together(
    request: Request,
    product_id: str,
    limit: int = Query(5, ge=1, le=20)
):
    """
    Get recommendations based on "Frequently Bought Together" pattern
    """
    # Check cache
    cache_key = f"fbt_rec:{product_id}:{limit}"
    cached_result = recommendations_cache.get(cache_key)
    if cached_result:
        return cached_result
    
    # Start timing
    start_time = time.time()
    
    # Get recommendations
    recommendations = await get_recommender().get_product_recommendations(product_id, limit)
    
    # Cache result
    recommendations_cache.set(cache_key, recommendations)
    
    # Record processing time
    request.state.processing_time = time.time() - start_time
    
    return recommendations
