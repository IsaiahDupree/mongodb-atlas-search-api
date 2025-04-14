from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import IndexModel, ASCENDING, TEXT
from pymongo.errors import OperationFailure
import os
from typing import Optional, Dict, Any
import functools

# Database connection objects with lazy initialization
class DB:
    client: Optional[AsyncIOMotorClient] = None
    db = None
    initialized = False
    
    @classmethod
    def initialize(cls, uri: Optional[str] = None, db_name: Optional[str] = None):
        """Initialize database connection"""
        if cls.initialized and cls.client and cls.db:
            return
            
        # Get URI from params or environment
        mongodb_uri = uri or os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        
        # Extract database name from URI or use provided name
        if db_name:
            database_name = db_name
        else:
            # Extract database name from URI or default to 'productdb'
            if '/' in mongodb_uri.split('://')[-1]:
                database_name = mongodb_uri.split('/')[-1]
                if '?' in database_name:
                    database_name = database_name.split('?')[0]
            else:
                database_name = "productdb"
        
        try:
            cls.client = AsyncIOMotorClient(mongodb_uri)
            cls.db = cls.client[database_name]
            cls.initialized = True
        except Exception as e:
            print(f"Failed to initialize MongoDB connection: {e}")
            # For testing environments, provide a mock DB
            if os.getenv("TESTING", "false").lower() == "true":
                print("Using mock database for testing")
                from unittest.mock import MagicMock, AsyncMock
                cls.client = MagicMock()
                cls.db = MagicMock()
                cls.db.command = AsyncMock(return_value={"ok": 1})
                cls.db.list_collection_names = AsyncMock(return_value=["products", "orderlines", "product_pairs"])
                cls.db.products = MagicMock()
                cls.db.orderlines = MagicMock()
                cls.db.product_pairs = MagicMock()
                cls.initialized = True

# Singleton instance
db = DB()

async def init_indexes():
    """
    Initialize the necessary indexes for MongoDB collections.
    This includes text indexes and vector indexes for search functionality.
    """
    # Product collection indexes
    try:
        # Basic indexes for common queries
        await db.db.products.create_index("id", unique=True)
        await db.db.products.create_index("brand")
        await db.db.products.create_index("color")
        await db.db.products.create_index("productType")
        
        # Text index for keyword searches
        await db.db.products.create_index([
            ("title", "text"), 
            ("description", "text"),
            ("brand", "text")
        ], default_language="norwegian")
        
        # Vector index for MongoDB Atlas Search
        # Note: This is a simplified version. For a real MongoDB Atlas deployment,
        # you would need to configure this through the Atlas UI or API
        vector_index = {
            "mappings": {
                "dynamic": True,
                "fields": {
                    "title_embedding": {
                        "type": "knnVector",
                        "dimensions": 384,  # Dimensions for paraphrase-multilingual-MiniLM-L12-v2
                        "similarity": "cosine"
                    },
                    "description_embedding": {
                        "type": "knnVector",
                        "dimensions": 384,
                        "similarity": "cosine"
                    }
                }
            }
        }
        
        # In a real scenario, you'd use Atlas Search API to create this index
        # Here we're just printing instructions for demonstration
        print("For MongoDB Atlas, create a vector search index with the following configuration:")
        print(vector_index)
        
        # Orderlines indexes
        await db.db.orderlines.create_index([("orderNr", ASCENDING), ("productNr", ASCENDING)])
        await db.db.orderlines.create_index("customerNr")
        await db.db.orderlines.create_index("productNr")
        
        print("Database indexes initialized successfully")
    except OperationFailure as e:
        print(f"Error creating indexes: {e}")
        # Continue anyway as this might be a permissions issue or the indexes already exist
    
async def get_db() -> Any:
    """Get the database instance, initializing if needed"""
    if not db.initialized:
        db.initialize()
    return db.db

async def get_product_collection():
    """Return the products collection"""
    if not db.initialized:
        db.initialize()
    return db.db.products

async def get_orderlines_collection():
    """Return the orderlines collection"""
    if not db.initialized:
        db.initialize()
    return db.db.orderlines

async def get_product_pairs_collection():
    """Return the product_pairs collection"""
    if not db.initialized:
        db.initialize()
    return db.db.product_pairs
