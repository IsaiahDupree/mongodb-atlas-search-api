#!/usr/bin/env python3
"""
Script to help set up and validate MongoDB Atlas search index configuration.
This script requires the mongodb-atlas package.
"""

import os
import json
import argparse
import sys
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Default MongoDB URI from environment variable
DEFAULT_MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/productdb")
DEFAULT_DATABASE_NAME = "productdb"
DEFAULT_COLLECTION_NAME = "products"
DEFAULT_INDEX_NAME = "product_search"

def check_atlas_connection(mongodb_uri):
    """Check connection to MongoDB Atlas"""
    try:
        client = MongoClient(mongodb_uri)
        # Check connection by issuing a simple command
        client.admin.command('ping')
        print("✅ Successfully connected to MongoDB")
        return client
    except Exception as e:
        print(f"❌ Error connecting to MongoDB: {str(e)}")
        return None

def get_index_definition():
    """Return the vector search index definition"""
    return {
        "mappings": {
            "dynamic": True,
            "fields": {
                "title_embedding": {
                    "type": "knnVector",
                    "dimensions": 384,
                    "similarity": "cosine"
                },
                "description_embedding": {
                    "type": "knnVector",
                    "dimensions": 384,
                    "similarity": "cosine"
                },
                "title": {
                    "type": "string"
                },
                "description": {
                    "type": "string"
                },
                "brand": {
                    "type": "string"
                },
                "color": {
                    "type": "string"
                },
                "ageBucket": {
                    "type": "string"
                },
                "isOnSale": {
                    "type": "boolean"
                },
                "seasons": {
                    "type": "string"
                }
            }
        }
    }

def check_index_exists(client, database_name, collection_name, index_name):
    """Check if Atlas Search index exists"""
    db = client[database_name]
    
    try:
        # List all indexes in the collection
        indexes = db.command("listSearchIndexes", collection_name)
        
        for index in indexes.get("cursor", {}).get("firstBatch", []):
            if index.get("name") == index_name:
                print(f"✅ Index '{index_name}' exists on collection '{collection_name}'")
                return True
        
        print(f"❌ Index '{index_name}' does not exist on collection '{collection_name}'")
        return False
    except Exception as e:
        print(f"❌ Error checking indexes: {str(e)}")
        return False

def check_collection_status(client, database_name, collection_name):
    """Check collection status and count documents"""
    db = client[database_name]
    collection = db[collection_name]
    
    try:
        # Count documents
        doc_count = collection.count_documents({})
        print(f"✅ Collection '{collection_name}' exists with {doc_count} documents")
        
        # Check for products with embeddings
        embedding_count = collection.count_documents({"title_embedding": {"$exists": True}})
        print(f"  - {embedding_count} documents have title embeddings")
        
        return True
    except Exception as e:
        print(f"❌ Error checking collection: {str(e)}")
        return False

def display_setup_instructions():
    """Display instructions for manual setup in Atlas"""
    index_definition = get_index_definition()
    
    print("\n==== Atlas Search Setup Instructions ====")
    print("\nTo create a vector search index in MongoDB Atlas:")
    print("1. Log in to your MongoDB Atlas account")
    print("2. Navigate to your cluster")
    print("3. Click on 'Search' tab")
    print("4. Click 'Create Index'")
    print("5. Select JSON Editor and enter the following configuration:")
    print("\n```json")
    print(json.dumps(index_definition, indent=2))
    print("```\n")
    print("6. Name your index 'product_search'")
    print("7. Select the 'productdb.products' namespace")
    print("8. Click 'Create Search Index'")
    print("\nNote: Index creation may take a few minutes to complete.")

def main():
    parser = argparse.ArgumentParser(description="Set up and validate MongoDB Atlas search index")
    parser.add_argument("--uri", default=DEFAULT_MONGODB_URI, help="MongoDB URI connection string")
    parser.add_argument("--database", default=DEFAULT_DATABASE_NAME, help="Database name")
    parser.add_argument("--collection", default=DEFAULT_COLLECTION_NAME, help="Collection name")
    parser.add_argument("--index", default=DEFAULT_INDEX_NAME, help="Search index name")
    parser.add_argument("--instructions", action="store_true", help="Display setup instructions only")
    
    args = parser.parse_args()
    
    if args.instructions:
        display_setup_instructions()
        return
    
    # Check connection
    client = check_atlas_connection(args.uri)
    if not client:
        print("Failed to connect to MongoDB. Please check your connection string.")
        sys.exit(1)
    
    # Check collection status
    check_collection_status(client, args.database, args.collection)
    
    # Check if index exists
    index_exists = check_index_exists(client, args.database, args.collection, args.index)
    
    if not index_exists:
        print("\n⚠️ The required Atlas Search index was not found.")
        display_setup_instructions()
    
    # Close client connection
    client.close()

if __name__ == "__main__":
    main()
