from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any
import time
import os

from database.mongodb import get_db

router = APIRouter(tags=["health"])

@router.get("/health", response_model=Dict[str, Any])
async def health_check():
    """
    Health check endpoint for monitoring system status.
    Verifies database connection and returns basic system information.
    Does not require API key authentication.
    """
    start_time = time.time()
    
    health_info = {
        "status": "healthy",
        "timestamp": time.time(),
        "version": os.environ.get("APP_VERSION", "1.0.0"),
        "services": {}
    }
    
    # Check database connection
    try:
        db = await get_db()
        await db.command("ping")
        health_info["database_connection"] = "ok"
        
        # Get collection stats
        try:
            products_stats = await db.command("collStats", "products")
            orderlines_stats = await db.command("collStats", "orderlines")
            product_pairs_stats = await db.command("collStats", "product_pairs")
            
            health_info["services"]["mongodb"] = {
                "status": "healthy",
                "collections": {
                    "products": {
                        "count": products_stats.get("count", 0),
                        "size_mb": round(products_stats.get("size", 0) / (1024 * 1024), 2)
                    },
                    "orderlines": {
                        "count": orderlines_stats.get("count", 0),
                        "size_mb": round(orderlines_stats.get("size", 0) / (1024 * 1024), 2)
                    },
                    "product_pairs": {
                        "count": product_pairs_stats.get("count", 0),
                        "size_mb": round(product_pairs_stats.get("size", 0) / (1024 * 1024), 2)
                    }
                }
            }
        except Exception as e:
            # Collection stats are not critical for health check
            health_info["services"]["mongodb"] = {
                "status": "healthy",
                "collections_stats": "unavailable"
            }
            
    except Exception as e:
        health_info["status"] = "unhealthy"
        health_info["database_connection"] = f"error: {str(e)}"
    
    # Add response time
    health_info["response_time_ms"] = round((time.time() - start_time) * 1000, 2)
    
    return health_info
