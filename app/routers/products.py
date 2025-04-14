from fastapi import APIRouter, HTTPException, status, Body
from typing import List, Optional

from models.product import Product, ProductInDB
from database.mongodb import get_product_collection
from services.embedding import embedding_service

router = APIRouter()

@router.post("/ingestProducts", status_code=status.HTTP_201_CREATED, response_model=List[str])
async def ingest_products(products: List[Product] = Body(...)):
    """
    Ingest one or more products, preprocesses them (including embedding generation),
    and writes to the MongoDB database.
    
    Returns the IDs of the ingested products.
    """
    # Get the product collection
    collection = await get_product_collection()
    ingested_ids = []
    
    # Process each product
    for product in products:
        try:
            # Generate embeddings for title and description
            title_embedding = embedding_service.generate_embedding(product.title)
            description_embedding = embedding_service.generate_embedding(product.description)
            
            # Create product with embeddings
            product_dict = product.dict()
            product_dict["title_embedding"] = title_embedding
            product_dict["description_embedding"] = description_embedding
            
            # Upsert product (insert or update)
            result = await collection.replace_one(
                {"id": product.id}, 
                product_dict, 
                upsert=True
            )
            
            ingested_ids.append(product.id)
            
        except Exception as e:
            # Log but continue processing other products
            print(f"Error ingesting product {product.id}: {str(e)}")
    
    return ingested_ids

@router.get("/doc/{product_id}", response_model=Product)
async def get_product(product_id: str):
    """
    Retrieve full document by product ID
    """
    collection = await get_product_collection()
    product = await collection.find_one({"id": product_id})
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )
    
    # Convert MongoDB _id to string and remove it from response
    if "_id" in product:
        del product["_id"]
    
    return product

@router.delete("/remove/product/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_product(product_id: str):
    """
    Remove a specific product by ID
    """
    collection = await get_product_collection()
    result = await collection.delete_one({"id": product_id})
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )
    
    return None

@router.delete("/remove/products/all", status_code=status.HTTP_204_NO_CONTENT)
async def remove_all_products():
    """
    Remove all products from the database
    """
    collection = await get_product_collection()
    await collection.delete_many({})
    return None
