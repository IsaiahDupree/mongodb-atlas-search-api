"""
Test script for MongoDB Atlas Search API data management endpoints
"""
import requests
import json
import time
import uuid
import datetime
from typing import Dict, Any, List

API_URL = "http://localhost:8000"
API_KEY = "dev_api_key_12345"
HEADERS = {"x-apikey": API_KEY}

def print_response(response):
    """Print response with formatting"""
    print(f"Status Code: {response.status_code}")
    try:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except:
        print(f"Response: {response.text}")
    print("-" * 50)

def create_test_product(product_id=None, title="Test Product", description="This is a test product for endpoint testing", price_original=299.99, price_current=249.99):
    """Helper function to create product test data"""
    if not product_id:
        product_id = f"test-product-{uuid.uuid4().hex[:8]}"
        
    return {
        "id": product_id,
        "title": title,
        "description": description,
        "brand": "Test Brand",
        "imageThumbnailUrl": "https://example.com/image.jpg",
        "priceOriginal": price_original,
        "priceCurrent": price_current,
        "isOnSale": price_current < price_original,
        "ageFrom": 1,
        "ageTo": 3,
        "ageBucket": "1 to 3 years",
        "color": "red",
        "seasons": ["winter", "spring"],
        "productType": "main",
        "seasonRelevancyFactor": 0.8,
        "stockLevel": 45
    }

def test_ingest_product():
    """Test creating a test product"""
    product_id = f"test-product-{uuid.uuid4().hex[:8]}"
    product_data = [create_test_product(product_id)]
    
    response = requests.post(
        f"{API_URL}/ingest/products",
        headers=HEADERS,
        json=product_data
    )
    
    print("\n=== INSERTING TEST PRODUCT ===")
    print_response(response)
    
    return product_id

def create_test_order(product_id, order_id=None, customer_id=None, season="winter"):
    """Helper function to create order test data"""
    if not order_id:
        order_id = f"order-{uuid.uuid4().hex[:8]}"
    if not customer_id:
        customer_id = f"cust-{uuid.uuid4().hex[:8]}"
        
    return {
        "orderNr": order_id,
        "productNr": product_id,
        "customerNr": customer_id,
        "seasonName": season,
        "dateTime": datetime.datetime.now().isoformat()
    }

def test_ingest_order(product_id):
    """Test creating a test order"""
    order_id = f"order-{uuid.uuid4().hex[:8]}"
    customer_id = f"cust-{uuid.uuid4().hex[:8]}"
    
    order_data = [create_test_order(product_id, order_id, customer_id)]
    
    response = requests.post(
        f"{API_URL}/ingest/orderlines",
        headers=HEADERS,
        json=order_data
    )
    
    print("\n=== INSERTING TEST ORDER ===")
    print_response(response)
    
    return order_id, customer_id

def test_delete_product(product_id):
    """Test deleting a product"""
    response = requests.delete(
        f"{API_URL}/admin/remove/product/{product_id}",
        headers=HEADERS
    )
    
    print("\n=== DELETING PRODUCT ===")
    print_response(response)

def test_delete_order(order_id):
    """Test deleting an order"""
    response = requests.delete(
        f"{API_URL}/admin/remove/order/{order_id}",
        headers=HEADERS
    )
    
    print("\n=== DELETING ORDER ===")
    print_response(response)

def test_delete_user_orders(customer_id):
    """Test deleting all orders for a user"""
    response = requests.delete(
        f"{API_URL}/admin/remove/orders/user/{customer_id}",
        headers=HEADERS
    )
    
    print("\n=== DELETING USER ORDERS ===")
    print_response(response)

def test_delete_all_products():
    """Test deleting all products"""
    response = requests.delete(
        f"{API_URL}/admin/remove/products/all",
        headers=HEADERS
    )
    
    print("\n=== DELETING ALL PRODUCTS ===")
    print_response(response)

def test_delete_all_orders():
    """Test deleting all orders"""
    response = requests.delete(
        f"{API_URL}/admin/remove/orders/all",
        headers=HEADERS
    )
    
    print("\n=== DELETING ALL ORDERS ===")
    print_response(response)

def test_product_update():
    """Test updating an existing product"""
    # Create initial product
    product_id = f"test-product-{uuid.uuid4().hex[:8]}"
    initial_product = create_test_product(product_id, title="Initial Title", price_original=199.99, price_current=199.99)
    
    # Insert the product
    response = requests.post(
        f"{API_URL}/ingest/products",
        headers=HEADERS,
        json=[initial_product]
    )
    
    print("\n=== INSERTING INITIAL PRODUCT FOR UPDATE TEST ===")
    print_response(response)
    
    # Update the product with new values
    updated_product = create_test_product(product_id, title="Updated Title", price_original=199.99, price_current=149.99)
    
    # Update the product
    response = requests.post(
        f"{API_URL}/ingest/products",
        headers=HEADERS,
        json=[updated_product]
    )
    
    print("\n=== UPDATING PRODUCT ===")
    print_response(response)
    
    return product_id

def test_customer_multiple_orders():
    """Test creating multiple orders for the same customer"""
    # Create two products
    product_id1 = test_ingest_product()
    product_id2 = test_ingest_product()
    
    # Create a shared customer ID
    customer_id = f"cust-{uuid.uuid4().hex[:8]}"
    
    # Create multiple orders for the same customer
    order_data = [
        create_test_order(product_id1, customer_id=customer_id, season="winter"),
        create_test_order(product_id2, customer_id=customer_id, season="summer")
    ]
    
    response = requests.post(
        f"{API_URL}/ingest/orderlines",
        headers=HEADERS,
        json=order_data
    )
    
    print("\n=== INSERTING MULTIPLE ORDERS FOR SAME CUSTOMER ===")
    print_response(response)
    
    # Test deleting all orders for this customer
    test_delete_user_orders(customer_id)
    
    return product_id1, product_id2

def test_error_handling():
    """Test API error handling"""
    # Test invalid API key
    invalid_headers = {"x-apikey": "invalid_key_12345"}
    
    response = requests.get(
        f"{API_URL}/admin/metrics",
        headers=invalid_headers
    )
    
    print("\n=== TESTING INVALID API KEY ===")
    print_response(response)
    
    # Test invalid product ID in deletion
    response = requests.delete(
        f"{API_URL}/admin/remove/product/nonexistent-product-id",
        headers=HEADERS
    )
    
    print("\n=== TESTING INVALID PRODUCT ID DELETION ===")
    print_response(response)

def test_search_functionality():
    """Test search functionality after ingesting products"""
    # Create products with different properties for testing search
    product1 = create_test_product(title="Red Baby Shoes", description="Comfortable shoes for babies")
    product2 = create_test_product(title="Blue Baby Jacket", description="Warm jacket for babies")
    product3 = create_test_product(title="Adult T-Shirt", description="Cotton t-shirt for adults") 
    
    # Insert the products
    response = requests.post(
        f"{API_URL}/ingest/products",
        headers=HEADERS,
        json=[product1, product2, product3]
    )
    
    print("\n=== INSERTING PRODUCTS FOR SEARCH TEST ===")
    print_response(response)
    
    time.sleep(1)  # Allow time for indexing
    
    # Test search by keyword
    search_query = {"query": "baby", "limit": 10}
    response = requests.post(
        f"{API_URL}/search",
        headers=HEADERS,
        json=search_query
    )
    
    print("\n=== TESTING KEYWORD SEARCH ===")
    print_response(response)
    
    # Clean up the inserted products
    test_delete_all_products()

def main():
    """Run all tests"""
    print("==== TESTING DATA MANAGEMENT ENDPOINTS ====")
    
    # Insert test data
    product_id = test_ingest_product()
    order_id, user_id = test_ingest_order(product_id)
    
    # Wait a moment for data to be processed
    time.sleep(1)
    
    # Test delete endpoints
    try:
        # Basic CRUD operations
        test_delete_product(product_id)
        
        # Insert another product for testing
        product_id = test_ingest_product()
        order_id, user_id = test_ingest_order(product_id)
        
        time.sleep(1)
        
        # Test order deletion
        test_delete_order(order_id)
        
        # Insert another order
        order_id, _ = test_ingest_order(product_id)
        
        time.sleep(1)
        
        # Test user order deletion
        test_delete_user_orders(user_id)
        
        # Advanced test cases
        print("\n\n==== ADVANCED TEST CASES ====")
        
        # Test product update
        updated_product_id = test_product_update()
        
        # Test customer with multiple orders
        product_ids = test_customer_multiple_orders()
        
        # Test error handling
        test_error_handling()
        
        # Test search functionality
        test_search_functionality()
        
        # Insert multiple products/orders for testing bulk deletion
        print("\n\n==== FINAL CLEANUP ====")
        for _ in range(3):
            pid = test_ingest_product()
            test_ingest_order(pid)
        
        time.sleep(1)
        
        # Test bulk deletion
        test_delete_all_products()
        test_delete_all_orders()
        
    except Exception as e:
        print(f"Error during testing: {str(e)}")

if __name__ == "__main__":
    main()
