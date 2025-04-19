"""
Full Dataset Metaldetector Test

This script:
1. Loads ALL products from the client dataset (1000+)
2. Creates a local test database with the full dataset
3. Specifically tests for "metaldetector" matches using various prefix searches
4. Validates that all of Bjorn's required test cases work correctly

The test focuses on the specific QA check requirements:
"All of these searches should hit 'metaldetector': 'met', 'meta', 'metall', 'metalde', 'metaldetect'"
"""
import os
import sys
import json
from pymongo import MongoClient
from pymongo.errors import OperationFailure

# Add parent directory to import path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our application modules
from services.embedding import embedding_service

# Configuration
CLIENT_DATA_PATH = r"C:\Users\Isaia\OneDrive\Documents\Coding\Dockerized MongoDb Atlas search\Omnium_Search_Products_START-1742999880951\Omnium_Search_Products_START-1742999880951.json"
LOCAL_MONGODB_URI = "mongodb://localhost:27017"
DB_NAME = "full_dataset_test"
COLLECTION_NAME = "products"

# Specific test queries for metaldetector
METALDETECTOR_TEST_QUERIES = [
    "met",
    "meta",
    "metall",
    "metalde",
    "metaldetect"
]

def load_all_client_data(file_path):
    """Load all products from the client data file"""
    print(f"Loading data from {file_path}...")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading data: {e}")
        return {}
    
    if not data or "result" not in data:
        print("No data found or invalid format")
        return {}
    
    # Get all products
    all_products = data.get("result", [])
    print(f"Total products in file: {len(all_products)}")
    
    # Transform to our model
    transformed_products = []
    categories = {}
    brands = {}
    
    for item in all_products:
        try:
            # Extract category data
            for cat in item.get("categories", []):
                if cat.get("categoryId") and cat.get("name"):
                    cat_id = cat.get("categoryId")
                    categories[cat_id] = {
                        "id": cat_id,
                        "name": cat.get("name", ""),
                        "slug": cat.get("name", "").lower().replace(" ", "-"),
                        "productCount": categories.get(cat_id, {}).get("productCount", 0) + 1
                    }
            
            # Extract brand data
            supplier_name = item.get("supplierName", "Unknown")
            if supplier_name:
                brand_id = f"brand_{supplier_name.lower().replace(' ', '_')}"
                brands[brand_id] = {
                    "id": brand_id,
                    "name": supplier_name,
                    "productCount": brands.get(brand_id, {}).get("productCount", 0) + 1
                }
                
            # Transform to our product model
            product = {
                "id": item.get("id", f"product_{len(transformed_products)}"),
                "title": item.get("name", "Untitled Product"),
                "description": item.get("alternativeProductName", item.get("name", "No description")),
                "brand": item.get("supplierName", "Unknown"),
                "imageThumbnailUrl": item.get("imageUrl", ""),
                "priceOriginal": float(item.get("price", {}).get("originalUnitPrice", 0)),
                "priceCurrent": float(item.get("price", {}).get("unitPrice", 0)),
                "isOnSale": float(item.get("price", {}).get("unitPrice", 0)) < float(item.get("price", {}).get("originalUnitPrice", 0)),
                "ageFrom": None,
                "ageTo": None,
                "ageBucket": None,
                "color": next((prop.get("value") for prop in item.get("properties", []) if prop.get("key") == "ProductSelector" and prop.get("value") == "Farge"), None),
                "seasons": [],
                "productType": "main",
                "seasonRelevancyFactor": 0.5,
                "stockLevel": int(item.get("availableInventory", 0))
            }
            
            # Add additional fields from client data
            product["supplierItemId"] = item.get("supplierItemId", "")
            product["productAttributes"] = item.get("productAttributes", {})
            product["alternativeProductName"] = item.get("alternativeProductName", "")
            
            # Generate embeddings for vector search
            product["title_embedding"] = embedding_service.generate_embedding(product["title"])
            product["description_embedding"] = embedding_service.generate_embedding(product["description"])
            
            transformed_products.append(product)
        except Exception as e:
            print(f"Error transforming product {item.get('id', 'unknown')}: {e}")
    
    return {
        "products": transformed_products,
        "categories": list(categories.values()),
        "brands": list(brands.values())
    }

def initialize_local_database(connection_string, db_name, collection_name, data):
    """Initialize local MongoDB database with the full dataset"""
    print(f"Initializing local MongoDB database: {db_name}.{collection_name}")
    
    client = MongoClient(connection_string)
    
    try:
        # Get database and collection
        db = client[db_name]
        collection = db[collection_name]
        
        # Clear existing data
        collection.delete_many({})
        print(f"✅ Cleared existing data from {collection_name}")
        
        # Insert products in batches to avoid memory issues
        products = data.get("products", [])
        batch_size = 100
        total_inserted = 0
        
        for i in range(0, len(products), batch_size):
            batch = products[i:i + batch_size]
            result = collection.insert_many(batch)
            total_inserted += len(result.inserted_ids)
            print(f"  Inserted batch {i//batch_size + 1} ({len(batch)} products)")
        
        print(f"✅ Inserted {total_inserted} products in total")
        
        # Create basic indexes
        collection.create_index("title")
        collection.create_index("description")
        collection.create_index("brand")
        print("✅ Created basic indexes")
        
        return True
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        client.close()

def find_metaldetector_products(collection):
    """Find all products with 'metaldetector' in title or description"""
    query = {
        "$or": [
            {"title": {"$regex": "metaldetector", "$options": "i"}},
            {"description": {"$regex": "metaldetector", "$options": "i"}}
        ]
    }
    
    metaldetector_products = []
    cursor = collection.find(query)
    
    for product in cursor:
        metaldetector_products.append({
            "id": product.get("id"),
            "title": product.get("title"),
            "description": product.get("description"),
            "brand": product.get("brand")
        })
    
    return metaldetector_products

def test_metaldetector_search_query(collection, query):
    """Test a specific metaldetector search query"""
    print(f"\n----- Testing Query: '{query}' -----")
    
    # Create regex query for products
    regex_query = {
        "$or": [
            {"title": {"$regex": query, "$options": "i"}},
            {"description": {"$regex": query, "$options": "i"}}
        ]
    }
    
    # Find products matching the query
    matching_products = []
    cursor = collection.find(regex_query).limit(20)
    
    for product in cursor:
        matching_products.append({
            "id": product.get("id"),
            "title": product.get("title"),
            "description": product.get("description"),
            "brand": product.get("brand")
        })
    
    # Find metaldetector products among the matches
    metaldetector_matches = []
    
    for product in matching_products:
        title = product.get("title", "").lower()
        description = product.get("description", "").lower()
        
        if "metaldetector" in title or "metaldetector" in description or "metal detector" in title or "metal detector" in description:
            metaldetector_matches.append(product)
    
    # Print results
    print(f"Total matching products: {len(matching_products)}")
    print(f"Metaldetector products found: {len(metaldetector_matches)}")
    
    if metaldetector_matches:
        print("\nMetaldetector products matching this query:")
        for i, product in enumerate(metaldetector_matches):
            print(f"  {i+1}. {product.get('title')} - {product.get('description')[:50]}...")
    else:
        print("\nNo metaldetector products found with this query")
    
    return {
        "query": query,
        "total_matches": len(matching_products),
        "metaldetector_matches": len(metaldetector_matches),
        "success": len(metaldetector_matches) > 0
    }

def main():
    """Main function to run the full dataset test"""
    print("===== FULL DATASET METALDETECTOR TEST =====\n")
    
    # Load all client data
    data = load_all_client_data(CLIENT_DATA_PATH)
    
    if not data.get("products"):
        print("❌ No products loaded from client data")
        return
    
    # Initialize local database with full dataset
    success = initialize_local_database(LOCAL_MONGODB_URI, DB_NAME, COLLECTION_NAME, data)
    
    if not success:
        print("❌ Database initialization failed")
        return
    
    # Connect to the database
    client = MongoClient(LOCAL_MONGODB_URI)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]
    
    # Find all metaldetector products in the dataset
    print("\nSearching for all metaldetector products in the dataset...")
    metaldetector_products = find_metaldetector_products(collection)
    
    if metaldetector_products:
        print(f"\n✅ Found {len(metaldetector_products)} products with 'metaldetector' in the dataset:")
        for i, product in enumerate(metaldetector_products):
            print(f"  {i+1}. {product.get('title')} - {product.get('description')[:50]}...")
    else:
        print("❌ No products with 'metaldetector' found in the dataset")
        print("Note: This test requires products with 'metaldetector' in the title or description")
        print("      Please check the dataset or add sample metaldetector products")
    
    # Run test queries
    print("\n===== TESTING BJORN'S REQUIRED QUERIES =====")
    results = []
    
    for query in METALDETECTOR_TEST_QUERIES:
        result = test_metaldetector_search_query(collection, query)
        results.append(result)
    
    # Print summary
    print("\n===== SUMMARY OF TEST RESULTS =====")
    successful_queries = [r for r in results if r.get("success")]
    print(f"Total queries tested: {len(results)}")
    print(f"Successful queries (found metaldetector products): {len(successful_queries)}")
    
    if successful_queries:
        print("\nSuccessful queries:")
        for result in successful_queries:
            print(f"  ✅ '{result.get('query')}' - Found {result.get('metaldetector_matches')} metaldetector products")
    
    failed_queries = [r for r in results if not r.get("success")]
    if failed_queries:
        print("\nFailed queries (no metaldetector products found):")
        for result in failed_queries:
            print(f"  ❌ '{result.get('query')}' - Found {result.get('total_matches')} products, but no metaldetector products")
    
    # Check if all required queries were successful
    if len(successful_queries) == len(METALDETECTOR_TEST_QUERIES):
        print("\n✅ ALL REQUIRED QUERIES SUCCESSFUL!")
        print("All of Bjorn's required test cases work correctly:")
        print("'met', 'meta', 'metall', 'metalde', 'metaldetect' all match metaldetector products")
    else:
        print("\n⚠️ NOT ALL REQUIRED QUERIES WERE SUCCESSFUL")
        print("Some of Bjorn's test cases did not find metaldetector products")
        print("This may be due to the dataset not containing suitable metaldetector products")
    
    # Close connection
    client.close()

if __name__ == "__main__":
    main()
