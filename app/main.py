from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
from contextlib import asynccontextmanager
import time

import os
from routers import products, orders, admin, naive_recommender, health, ingest

# Conditionally import the appropriate search router based on TEST_MODE
TEST_MODE = os.environ.get("TEST_MODE", "false").lower() in ("true", "1", "yes")
if TEST_MODE:
    from routers import search_local as search
    print("Using simplified search implementation for LOCAL TESTING")
else:
    from routers import search
    print("Using production search implementation with MongoDB Atlas Search")
from dependencies import get_api_key
from database.mongodb import db
from services.monitoring import APIMonitoringMiddleware, SearchMetrics
from services.benchmarking import performance_tracker

# Lifespan for FastAPI
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database connection
    mongodb_uri = os.getenv("MONGODB_URI", "mongodb://mongodb:27017")
    
    # Initialize the database with our improved approach
    db.initialize(mongodb_uri)
    
    # Store references in app state for middleware access
    app.mongodb_client = db.client
    app.mongodb = db.db
    
    # Initialize vector search indices if needed
    from database.mongodb import init_indexes
    await init_indexes()
    
    # Ensure required collections exist
    collections = await db.db.list_collection_names()
    if "product_pairs" not in collections:
        await db.db.create_collection("product_pairs")
    
    print(f"Connected to MongoDB at {mongodb_uri}")
    yield
    # Cleanup
    if db.client:
        db.client.close()
    print("MongoDB connection closed")

# Create FastAPI app
app = FastAPI(
    title="Product Search and Recommendation API",
    description="API for vector search and product recommendations using MongoDB Atlas",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add monitoring middleware
app.add_middleware(APIMonitoringMiddleware)

# Include routers
app.include_router(products.router, tags=["Products"], dependencies=[Depends(get_api_key)])
app.include_router(orders.router, tags=["Orders"], dependencies=[Depends(get_api_key)])
# Search router now includes its own dependencies
app.include_router(search.router)
app.include_router(admin.router)
app.include_router(naive_recommender.router)
app.include_router(ingest.router)
# Health router does not require API key authentication
app.include_router(health.router)

# Health check endpoint is now in health.router

# API monitoring endpoints
@app.get("/api-stats", tags=["Monitoring"], dependencies=[Depends(get_api_key)])
async def api_stats():
    """Get API usage statistics and metrics"""
    return {
        "search_metrics": {
            "average_processing_time": SearchMetrics.get_average_processing_time(),
            "popular_queries": SearchMetrics.get_popular_queries(),
            "recent_searches": SearchMetrics.get_recent_searches(10)
        }
    }

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Middleware to add processing time to all responses"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
