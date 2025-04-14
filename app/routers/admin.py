"""
Administration router for MongoDB Atlas Search API
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio

from services.monitoring import SearchMetrics
from services.benchmarking import performance_tracker
from services.cache import search_cache, product_cache, recommendations_cache
from database.mongodb import get_product_collection, get_orderlines_collection, get_product_pairs_collection
from dependencies import get_api_key

router = APIRouter(
    prefix="/admin",
    tags=["Administration"],
    dependencies=[Depends(get_api_key)]
)

@router.get("/metrics", response_model=Dict[str, Any])
async def get_metrics(
    time_window_minutes: Optional[int] = Query(60, description="Time window for metrics in minutes")
):
    """
    Get API performance metrics for the specified time window
    """
    # Calculate the search metrics
    search_stats = performance_tracker.get_search_stats(time_window_minutes)
    
    # Get recommendation algorithm stats
    recommendation_stats = {
        "hybrid": performance_tracker.get_recommendation_stats("hybrid"),
        "co_occurrence": performance_tracker.get_recommendation_stats("co_occurrence"),
        "embedding": performance_tracker.get_recommendation_stats("embedding")
    }
    
    # Get endpoint performance stats
    endpoint_stats = performance_tracker.get_endpoint_stats()
    
    # Get cache statistics
    cache_stats = {
        "search_cache": search_cache.get_stats(),
        "product_cache": product_cache.get_stats(),
        "recommendations_cache": recommendations_cache.get_stats()
    }
    
    # Compile all metrics
    return {
        "timestamp": datetime.now().isoformat(),
        "time_window_minutes": time_window_minutes,
        "search_performance": search_stats,
        "recommendation_performance": recommendation_stats,
        "endpoint_performance": endpoint_stats,
        "cache_statistics": cache_stats,
        "search_metrics": {
            "popular_queries": SearchMetrics.get_popular_queries(10),
            "avg_processing_time": SearchMetrics.get_average_processing_time(100)
        }
    }


@router.delete("/remove/product/{product_id}", response_model=Dict[str, Any])
async def delete_product(
    product_id: str = Path(..., description="The ID of the product to delete")
):
    """
    Delete a single product by its ID
    
    This endpoint removes a product from the database and clears associated cache entries.
    """
    try:
        # Get product collection
        collection = await get_product_collection()
        
        # Delete the product
        result = await collection.delete_one({"id": product_id})
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID {product_id} not found"
            )
        
        # Clear product from cache
        product_cache.remove(product_id)
        
        # Invalidate related search caches since results may have included this product
        search_cache.clear()
        
        return {
            "status": "success",
            "message": f"Product {product_id} deleted successfully"
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete product: {str(e)}"
            )


@router.delete("/remove/products/all", response_model=Dict[str, Any])
async def delete_all_products():
    """
    Delete all products from the database
    
    This is a destructive operation that removes all products from the database
    and clears all cache entries. Use with caution.
    """
    try:
        # Get collections
        product_collection = await get_product_collection()
        product_pairs_collection = await get_product_pairs_collection()
        
        # Count documents before deletion
        product_count = await product_collection.count_documents({})
        
        # Delete all products
        await product_collection.delete_many({})
        
        # Delete all product pairs used for recommendations
        await product_pairs_collection.delete_many({})
        
        # Clear all caches
        product_cache.clear()
        search_cache.clear()
        recommendations_cache.clear()
        
        return {
            "status": "success",
            "message": f"All products deleted successfully",
            "deleted_count": product_count
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete all products: {str(e)}"
        )


@router.delete("/remove/order/{order_id}", response_model=Dict[str, Any])
async def delete_order(
    order_id: str = Path(..., description="The ID of the order to delete")
):
    """
    Delete a single order by its ID
    
    This endpoint removes an order from the database and its associated orderlines.
    """
    try:
        # Get orderlines collection
        collection = await get_orderlines_collection()
        
        # Delete the orderlines for this order ID
        result = await collection.delete_many({"orderNr": order_id})
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order with ID {order_id} not found or has no orderlines"
            )
        
        # No need to invalidate product cache as orders don't affect product data
        # But we should clear recommendation caches as they may depend on order history
        recommendations_cache.clear()
        
        return {
            "status": "success",
            "message": f"Order {order_id} deleted successfully",
            "deleted_count": result.deleted_count
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete order: {str(e)}"
            )


@router.delete("/remove/orders/all", response_model=Dict[str, Any])
async def delete_all_orders():
    """
    Delete all orders from the database
    
    This is a destructive operation that removes all orderlines from the database.
    This will affect recommendation systems that rely on order history.
    """
    try:
        # Get orderlines collection
        collection = await get_orderlines_collection()
        
        # Count documents before deletion
        order_count = await collection.count_documents({})
        
        # Delete all orderlines
        await collection.delete_many({})
        
        # Clear recommendations cache as it depends on order history
        recommendations_cache.clear()
        
        return {
            "status": "success",
            "message": f"All orders deleted successfully",
            "deleted_count": order_count
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete all orders: {str(e)}"
        )


@router.delete("/remove/orders/user/{user_id}", response_model=Dict[str, Any])
async def delete_user_orders(
    user_id: str = Path(..., description="The ID of the user whose orders to delete")
):
    """
    Delete all orders for a specific user
    
    This endpoint removes all orderlines associated with a specific user ID.
    This will affect recommendation systems that rely on that user's order history.
    """
    try:
        # Get orderlines collection
        collection = await get_orderlines_collection()
        
        # Count documents before deletion
        user_order_count = await collection.count_documents({"customerNr": user_id})
        
        if user_order_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} has no orders"
            )
        
        # Delete all orderlines for this user
        await collection.delete_many({"customerNr": user_id})
        
        # Clear specific user's recommendations from cache
        # This is a simple approach - ideally we would only invalidate this user's cache entries
        recommendations_cache.clear()
        
        return {
            "status": "success",
            "message": f"All orders for user {user_id} deleted successfully",
            "deleted_count": user_order_count
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete user orders: {str(e)}"
            )


@router.get("/cache/stats", response_model=Dict[str, Any])
async def cache_stats():
    """
    Get detailed statistics about the cache usage
    """
    return {
        "search_cache": search_cache.get_stats(),
        "product_cache": product_cache.get_stats(),
        "recommendations_cache": recommendations_cache.get_stats()
    }


@router.post("/cache/clear/{cache_type}", response_model=Dict[str, Any])
async def clear_cache(cache_type: str):
    """
    Clear a specific cache or all caches
    """
    if cache_type == "search":
        search_cache.clear()
        return {"status": "success", "message": "Search cache cleared"}
    elif cache_type == "product":
        product_cache.clear()
        return {"status": "success", "message": "Product cache cleared"}
    elif cache_type == "recommendations":
        recommendations_cache.clear()
        return {"status": "success", "message": "Recommendations cache cleared"}
    elif cache_type == "all":
        search_cache.clear()
        product_cache.clear()
        recommendations_cache.clear()
        return {"status": "success", "message": "All caches cleared"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid cache type: {cache_type}. Valid types: search, product, recommendations, all"
        )


@router.get("/performance/summary", response_model=Dict[str, Any])
async def performance_summary():
    """
    Get a high-level performance summary of the API
    """
    # Get metrics for different time windows
    last_hour = performance_tracker.get_search_stats(60)
    last_day = performance_tracker.get_search_stats(60 * 24)
    
    # Get endpoint stats
    endpoint_stats = performance_tracker.get_endpoint_stats()
    
    # Calculate overall API health score (0-100)
    # This is a simplified scoring system that considers:
    # - Search response times (lower is better)
    # - Success rates (higher is better)
    # - Cache hit rates (higher is better)
    
    # Base score starts at 100
    health_score = 100
    
    # Penalize for slow p95 response times
    if last_hour["p95_duration_ms"] > 500:  # > 500ms is slow
        penalty = min(30, (last_hour["p95_duration_ms"] - 500) / 20)
        health_score -= penalty
    
    # Penalize for low success rates in endpoints
    for endpoint, stats in endpoint_stats.items():
        if stats["success_rate"] < 0.99:  # < 99% success rate is concerning
            penalty = min(20, (0.99 - stats["success_rate"]) * 100)
            health_score -= penalty
    
    # Round and cap the health score
    health_score = max(0, min(100, round(health_score, 1)))
    
    # Determine status based on health score
    if health_score >= 90:
        status = "excellent"
    elif health_score >= 75:
        status = "good"
    elif health_score >= 50:
        status = "fair"
    else:
        status = "poor"
    
    return {
        "timestamp": datetime.now().isoformat(),
        "health_score": health_score,
        "status": status,
        "performance_summary": {
            "last_hour": {
                "search_avg_ms": last_hour["avg_duration_ms"],
                "search_p95_ms": last_hour["p95_duration_ms"],
                "search_count": last_hour["count"]
            },
            "last_day": {
                "search_avg_ms": last_day["avg_duration_ms"],
                "search_p95_ms": last_day["p95_duration_ms"],
                "search_count": last_day["count"]
            }
        },
        "cache_efficiency": {
            "search_cache_size": search_cache.get_stats()["size"],
            "product_cache_size": product_cache.get_stats()["size"],
            "recommendations_cache_size": recommendations_cache.get_stats()["size"]
        },
        "recommendations": {
            "recommendation_request_count": sum(
                stats["count"] for _, stats in performance_tracker.get_recommendation_stats().items()
            )
        }
    }
