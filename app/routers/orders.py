from fastapi import APIRouter, HTTPException, status, Body, Request, Query
from typing import List, Dict, Any, Optional
import time

from models.order import OrderLine, RecommendationQuery
from models.product import Product
from database.mongodb import get_orderlines_collection, get_product_collection
from services.recommendations import RecommendationEngine
from services.cache import recommendations_cache

router = APIRouter()

@router.post("/ingestOrderline", status_code=status.HTTP_201_CREATED)
async def ingest_orderline(orderline: OrderLine = Body(...)):
    """
    Ingests orderline data for use in product recommendations
    """
    collection = await get_orderlines_collection()
    
    # Convert to dict and insert
    orderline_dict = orderline.dict()
    
    # Convert datetime to string for MongoDB storage
    if isinstance(orderline_dict["dateTime"], str):
        pass  # Already a string
    else:
        orderline_dict["dateTime"] = orderline_dict["dateTime"].isoformat()
        
    await collection.insert_one(orderline_dict)
    
    return {"status": "success", "orderNr": orderline.orderNr, "productNr": orderline.productNr}

@router.post("/similar/{product_id}", response_model=List[Product])
async def similar_products(
    request: Request,
    product_id: str, 
    query: RecommendationQuery = None,
    algorithm: str = Query("hybrid", description="Recommendation algorithm: co_occurrence, embedding, or hybrid")
):
    """
    Find similar products based on purchase history.
    Implements "Users who bought X also bought these products" functionality.
    """
    if query is None:
        query = RecommendationQuery(productId=product_id)
    
    # Start timing for performance monitoring
    start_time = time.time()
    
    # Set up defaults
    if query is None:
        query = RecommendationQuery(productId=product_id)

    # Get collections
    product_collection = await get_product_collection()
    orderlines_collection = await get_orderlines_collection()
    
    # Select recommendation algorithm based on input parameter
    try:
        if algorithm == "co_occurrence":
            recommended_products = await RecommendationEngine.get_co_occurrence_recommendations(
                product_id, orderlines_collection, product_collection, limit=query.limit
            )
        elif algorithm == "embedding":
            recommended_products = await RecommendationEngine.get_embedding_similarity_recommendations(
                product_id, product_collection, limit=query.limit
            )
        else:  # hybrid (default)
            recommended_products = await RecommendationEngine.get_hybrid_recommendations(
                product_id, orderlines_collection, product_collection, limit=query.limit
            )
            
        # Record processing time
        processing_time = time.time() - start_time
        request.state.processing_time = processing_time
        
    except Exception as e:
        # Fallback to simple co-occurrence if any errors occur
        print(f"Recommendation engine error: {str(e)}. Using fallback method.")
        
        # Check if the product exists
        product = await product_collection.find_one({"id": product_id})
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID {product_id} not found"
            )
            
        # Simplified fallback implementation
        orders_with_product = await orderlines_collection.find(
            {"productNr": product_id}
        ).distinct("orderNr")
        
        if not orders_with_product:
            # If no orders found, return empty list
            return []
            
        pipeline = [
            {"$match": {"orderNr": {"$in": orders_with_product}, "productNr": {"$ne": product_id}}},
            {"$group": {"_id": "$productNr", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": query.limit}
        ]
        
        similar_products_cursor = orderlines_collection.aggregate(pipeline)
        similar_product_ids = [item["_id"] async for item in similar_products_cursor]
        
        # Fetch product details for the recommended products
        recommended_products = []
        if similar_product_ids:
            cursor = product_collection.find({"id": {"$in": similar_product_ids}})
            async for product in cursor:
                # Remove MongoDB _id and embedding vectors from response
                if "_id" in product:
                    del product["_id"]
                if "title_embedding" in product:
                    del product["title_embedding"]
                if "description_embedding" in product:
                    del product["description_embedding"]
                recommended_products.append(product)
    
    return recommended_products
