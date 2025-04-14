"""
Ingestion API for MongoDB Atlas Search
Handles ingestion of products and orderlines with embedding generation
"""
from fastapi import APIRouter, HTTPException, status, Body, Depends, Request
from typing import List, Dict, Any, Optional
import time

from models.product import Product, ProductInDB
from models.order import OrderLine
from database.mongodb import get_product_collection, get_orderlines_collection
from services.embedding import embedding_service
from dependencies import get_api_key

router = APIRouter(
    prefix="/ingest",
    tags=["Data Ingestion"],
    dependencies=[Depends(get_api_key)]
)

@router.post("/products", status_code=status.HTTP_201_CREATED)
async def ingest_products(request: Request, products: List[Product] = Body(...)):
    """
    Ingest products into the database
    
    - Accepts single or multiple products in a list
    - Generates embeddings for title and description fields
    - Stores products with embeddings in MongoDB
    """
    start_time = time.time()
    collection = await get_product_collection()
    
    # Process products with embedding generation
    inserted_count = 0
    updated_count = 0
    
    for product in products:
        # Generate embeddings
        title_embedding = embedding_service.generate_embedding(product.title)
        description_embedding = embedding_service.generate_embedding(product.description)
        
        # Create product document
        product_dict = product.dict()
        product_dict["title_embedding"] = title_embedding
        product_dict["description_embedding"] = description_embedding
        
        # Insert or update product
        try:
            # Check if product already exists
            existing = await collection.find_one({"id": product.id})
            
            if existing:
                # Update existing product
                await collection.replace_one(
                    {"id": product.id},
                    product_dict
                )
                updated_count += 1
            else:
                # Insert new product
                await collection.insert_one(product_dict)
                inserted_count += 1
                
        except Exception as e:
            # Log error and continue with next product
            print(f"Error ingesting product {product.id}: {str(e)}")
    
    processing_time = time.time() - start_time
    request.state.processing_time = processing_time
    
    return {
        "status": "success",
        "inserted": inserted_count,
        "updated": updated_count,
        "total_processed": len(products),
        "processing_time_ms": round(processing_time * 1000, 2)
    }

@router.post("/orderlines", status_code=status.HTTP_201_CREATED)
async def ingest_orderlines(request: Request, orderlines: List[OrderLine] = Body(...)):
    """
    Ingest orderlines into the database
    
    - Accepts single or multiple orderlines in a list
    - Stores order data for recommendation generation
    - Updates product relationship data for recommendations
    """
    start_time = time.time()
    collection = await get_orderlines_collection()
    
    # Process orderlines
    inserted_count = 0
    
    for orderline in orderlines:
        # Insert orderline
        try:
            await collection.insert_one(orderline.dict())
            inserted_count += 1
            
        except Exception as e:
            # Log error and continue with next orderline
            print(f"Error ingesting orderline {orderline.orderNr}/{orderline.productNr}: {str(e)}")
    
    # Optionally trigger recommendation pre-computation
    # This would be a background task in a real implementation
    
    processing_time = time.time() - start_time
    request.state.processing_time = processing_time
    
    return {
        "status": "success",
        "inserted": inserted_count,
        "total_processed": len(orderlines),
        "processing_time_ms": round(processing_time * 1000, 2)
    }

@router.post("/batch-import")
async def batch_import(request: Request, data: Dict[str, Any] = Body(...)):
    """
    Batch import both products and orderlines
    
    - Accepts a dictionary with 'products' and 'orderlines' keys
    - Processes both in a single request
    - Returns counts of inserted/updated items
    """
    results = {
        "products": {"processed": 0, "inserted": 0, "updated": 0},
        "orderlines": {"processed": 0, "inserted": 0}
    }
    
    # Process products if provided
    if "products" in data and isinstance(data["products"], list):
        products_result = await ingest_products(request, products=data["products"])
        results["products"]["processed"] = products_result["total_processed"]
        results["products"]["inserted"] = products_result["inserted"]
        results["products"]["updated"] = products_result["updated"]
    
    # Process orderlines if provided
    if "orderlines" in data and isinstance(data["orderlines"], list):
        orderlines_result = await ingest_orderlines(request, orderlines=data["orderlines"])
        results["orderlines"]["processed"] = orderlines_result["total_processed"]
        results["orderlines"]["inserted"] = orderlines_result["inserted"]
    
    return {
        "status": "success",
        "results": results
    }
