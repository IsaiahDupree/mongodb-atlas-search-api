#!/usr/bin/env python3
"""
Generate test data for the recommendation system.
This script creates realistic product and order data with patterns
that will make the recommendation system produce meaningful results.
"""

import json
import random
import datetime
import uuid
from typing import List, Dict, Any

# Configuration
NUM_PRODUCTS = 50
NUM_USERS = 20
NUM_ORDERS = 200
PRODUCTS_PER_ORDER_MIN = 1
PRODUCTS_PER_ORDER_MAX = 5
SEED = 42  # For reproducible results

# Set random seed
random.seed(SEED)

# Product categories
CATEGORIES = [
    "Toys", "Baby Clothes", "Strollers", "Car Seats", "Nursery", 
    "Feeding", "Bath", "Safety", "Health", "Educational"
]

# Brands
BRANDS = [
    "BabySteps", "KidComfort", "TinyTots", "BabyEssentials", "SmileKids",
    "LittleWorld", "BabyDreams", "KidsCare", "TinyMinds", "BabyZone"
]

# Colors
COLORS = ["red", "blue", "green", "yellow", "purple", "pink", "white", "black", "gray", "orange"]

# Age buckets
AGE_BUCKETS = ["0 to 1 years", "1 to 3 years", "3 to 5 years", "5 to 7 years", "7 to 10 years"]

# Seasons
SEASONS = ["spring", "summer", "autumn", "winter", "all"]

def generate_product_id() -> str:
    """Generate a product ID in the format 'prod' + 3 digits"""
    return f"prod{random.randint(100, 999)}"

def generate_product_title(category: str, brand: str) -> str:
    """Generate a product title based on category and brand"""
    adjectives = ["Comfortable", "Deluxe", "Premium", "Essential", "Quality", "Super", "Ultimate"]
    noun = category.lower() if random.random() < 0.5 else brand
    return f"{random.choice(adjectives)} {category} by {brand}"

def generate_product_description(title: str, color: str, age_bucket: str) -> str:
    """Generate a product description based on title, color and age bucket"""
    features = [
        "Easy to use", 
        "Durable material", 
        "Safe for children", 
        "BPA free", 
        "Award-winning design",
        "Loved by parents",
        "Doctor recommended",
        "Top seller"
    ]
    
    selected_features = random.sample(features, k=min(3, len(features)))
    
    return (
        f"{title} in {color}. Perfect for children in the {age_bucket} age range. "
        f"{'. '.join(selected_features)}. A great choice for your child!"
    )

def generate_products(num_products: int) -> List[Dict[str, Any]]:
    """Generate a list of realistic baby product data"""
    products = []
    used_ids = set()
    
    for _ in range(num_products):
        # Generate a unique product ID
        while True:
            product_id = generate_product_id()
            if product_id not in used_ids:
                used_ids.add(product_id)
                break
        
        category = random.choice(CATEGORIES)
        brand = random.choice(BRANDS)
        color = random.choice(COLORS)
        age_from, age_to = random.choice([(0, 1), (1, 3), (3, 5), (5, 7), (7, 10)])
        age_bucket = f"{age_from} to {age_to} years"
        
        price_original = round(random.uniform(99.99, 999.99), 2)
        is_on_sale = random.random() < 0.3
        price_current = round(price_original * random.uniform(0.7, 0.9), 2) if is_on_sale else price_original
        
        seasons_count = random.randint(1, len(SEASONS))
        if seasons_count == len(SEASONS):
            product_seasons = ["all"]
        else:
            product_seasons = random.sample([s for s in SEASONS if s != "all"], k=seasons_count)
        
        title = generate_product_title(category, brand)
        description = generate_product_description(title, color, age_bucket)
        
        product = {
            "id": product_id,
            "title": title,
            "description": description,
            "brand": brand,
            "imageThumbnailUrl": f"https://example.com/images/{product_id}.jpg",
            "priceOriginal": price_original,
            "priceCurrent": price_current,
            "isOnSale": is_on_sale,
            "ageFrom": age_from,
            "ageTo": age_to,
            "ageBucket": age_bucket,
            "color": color,
            "category": category,
            "seasons": product_seasons,
            "productType": random.choice(["main", "part", "extras"]),
            "seasonRelevancyFactor": round(random.uniform(0.1, 1.0), 1),
            "stockLevel": random.randint(0, 100)
        }
        
        products.append(product)
    
    return products

def generate_customer_id() -> str:
    """Generate a customer ID"""
    return f"cust{random.randint(1000, 9999)}"

def generate_order_id() -> str:
    """Generate an order ID"""
    return f"ORD-{uuid.uuid4().hex[:8]}"

def generate_order_date() -> str:
    """Generate a random date in the last year"""
    days_back = random.randint(1, 365)
    order_date = datetime.datetime.now() - datetime.timedelta(days=days_back)
    return order_date.isoformat()

def generate_orderlines(products: List[Dict[str, Any]], num_users: int, num_orders: int) -> List[Dict[str, Any]]:
    """
    Generate orderlines with realistic patterns for recommendation testing.
    Creates clusters of products that tend to be bought together.
    """
    # Create customer IDs
    customer_ids = [generate_customer_id() for _ in range(num_users)]
    
    # Create product clusters (products that tend to be bought together)
    # This will help create meaningful recommendation patterns
    product_clusters = []
    products_copy = products.copy()
    random.shuffle(products_copy)
    
    # Create 5-10 product clusters
    num_clusters = random.randint(5, 10)
    cluster_size = len(products) // num_clusters
    
    for i in range(0, len(products_copy), cluster_size):
        cluster = products_copy[i:i + cluster_size]
        if cluster:  # Ensure cluster is not empty
            product_clusters.append([p["id"] for p in cluster])
    
    orderlines = []
    
    for _ in range(num_orders):
        order_id = generate_order_id()
        customer_id = random.choice(customer_ids)
        order_date = generate_order_date()
        
        # Determine the season based on the order date
        month = datetime.datetime.fromisoformat(order_date).month
        if 3 <= month <= 5:
            season = "spring"
        elif 6 <= month <= 8:
            season = "summer"
        elif 9 <= month <= 11:
            season = "autumn"
        else:
            season = "winter"
        
        # Most orders will contain products from the same cluster
        # This creates patterns for the recommendation system to discover
        if random.random() < 0.8:
            cluster = random.choice(product_clusters)
            num_products = random.randint(
                PRODUCTS_PER_ORDER_MIN,
                min(PRODUCTS_PER_ORDER_MAX, len(cluster))
            )
            selected_products = random.sample(cluster, k=num_products)
        else:
            # Some orders will have random products
            all_product_ids = [p["id"] for p in products]
            num_products = random.randint(PRODUCTS_PER_ORDER_MIN, PRODUCTS_PER_ORDER_MAX)
            selected_products = random.sample(all_product_ids, k=num_products)
        
        # Create orderlines for each product
        for product_id in selected_products:
            orderline = {
                "orderNr": order_id,
                "productNr": product_id,
                "customerNr": customer_id,
                "seasonName": season,
                "dateTime": order_date,
                "orderLines": {
                    "productNr": product_id
                }
            }
            orderlines.append(orderline)
    
    return orderlines

def main():
    """Generate test data and save to JSON files"""
    print(f"Generating {NUM_PRODUCTS} products...")
    products = generate_products(NUM_PRODUCTS)
    
    print(f"Generating {NUM_ORDERS} orders for {NUM_USERS} users...")
    orderlines = generate_orderlines(products, NUM_USERS, NUM_ORDERS)
    
    # Save products to JSON file
    with open("sample_recommendation_products.json", "w", encoding="utf-8") as f:
        json.dump(products, f, indent=2, ensure_ascii=False)
    
    # Save orderlines to JSON file
    with open("sample_recommendation_orderlines.json", "w", encoding="utf-8") as f:
        json.dump(orderlines, f, indent=2, ensure_ascii=False)
    
    print("Data generation complete!")
    print(f"- Created {len(products)} products")
    print(f"- Created {len(orderlines)} orderlines across {NUM_ORDERS} orders")
    print(f"- Files saved to 'sample_recommendation_products.json' and 'sample_recommendation_orderlines.json'")

if __name__ == "__main__":
    main()
