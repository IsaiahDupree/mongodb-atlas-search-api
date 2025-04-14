#!/usr/bin/env python3
"""
Test script for the naive recommender system.
This script will load test data, generate product pairs, and then test various recommendation types.
"""

import os
import sys
import json
import asyncio
import argparse
import random
from typing import Dict, List, Any
from tabulate import tabulate
from pymongo import MongoClient
from pymongo.database import Database

# Add parent directory to path to import app modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from app.services.naive_recommender import NaiveRecommender
from app.services.embedding import embedding_service


class RecommenderTester:
    """Test harness for the naive recommender system"""
    
    def __init__(self, db: Database):
        """Initialize the tester with a MongoDB database"""
        self.db = db
        self.recommender = NaiveRecommender(db)
    
    async def setup_test_data(self, products_file: str, orders_file: str) -> Dict[str, int]:
        """
        Load test data into the database
        
        Args:
            products_file: Path to products JSON file
            orders_file: Path to orderlines JSON file
            
        Returns:
            Dictionary with counts of loaded data
        """
        # Clear existing collections
        await self.db.products.delete_many({})
        await self.db.orderlines.delete_many({})
        await self.db.product_pairs.delete_many({})
        
        # Load products
        with open(products_file, 'r', encoding='utf-8') as f:
            products = json.load(f)
        
        # Generate embeddings for products (optional)
        print("Generating embeddings for products...")
        for product in products:
            # Generate embeddings for title and description
            product["title_embedding"] = embedding_service.generate_embedding(product["title"])
            product["description_embedding"] = embedding_service.generate_embedding(product["description"])
        
        # Insert products
        if products:
            await self.db.products.insert_many(products)
        
        # Load orderlines
        with open(orders_file, 'r', encoding='utf-8') as f:
            orderlines = json.load(f)
        
        # Insert orderlines
        if orderlines:
            await self.db.orderlines.insert_many(orderlines)
        
        return {
            "products_count": len(products),
            "orderlines_count": len(orderlines),
            "unique_customers": len(set(order["customerNr"] for order in orderlines))
        }
    
    async def compute_product_pairs(self) -> Dict[str, Any]:
        """
        Compute product pairs for recommendation
        
        Returns:
            Statistics about the computation
        """
        print("Computing product pairs...")
        result = await self.recommender.pre_compute_product_pairs()
        return result
    
    async def test_collaborative_recommendations(self, user_id: str = None, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Test collaborative filtering recommendations
        
        Args:
            user_id: User ID to get recommendations for (random if None)
            limit: Maximum number of recommendations
            
        Returns:
            List of recommended products
        """
        # If no user ID provided, get a random one from the database
        if user_id is None:
            users = await self.db.orderlines.distinct("customerNr")
            if not users:
                print("No users found in database")
                return []
            user_id = random.choice(users)
        
        print(f"Getting collaborative recommendations for user {user_id}...")
        recommendations = await self.recommender.get_collaborative_recommendations(user_id, limit)
        return recommendations
    
    async def test_content_based_recommendations(self, product_id: str = None, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Test content-based recommendations
        
        Args:
            product_id: Product ID to get recommendations for (random if None)
            limit: Maximum number of recommendations
            
        Returns:
            List of recommended products
        """
        # If no product ID provided, get a random one from the database
        if product_id is None:
            products = await self.db.products.distinct("id")
            if not products:
                print("No products found in database")
                return []
            product_id = random.choice(products)
        
        print(f"Getting content-based recommendations for product {product_id}...")
        recommendations = await self.recommender.get_content_based_recommendations(product_id, limit)
        return recommendations
    
    async def test_hybrid_recommendations(self, user_id: str = None, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Test hybrid recommendations
        
        Args:
            user_id: User ID to get recommendations for (random if None)
            limit: Maximum number of recommendations
            
        Returns:
            List of recommended products
        """
        # If no user ID provided, get a random one from the database
        if user_id is None:
            users = await self.db.orderlines.distinct("customerNr")
            if not users:
                print("No users found in database")
                return []
            user_id = random.choice(users)
        
        print(f"Getting hybrid recommendations for user {user_id}...")
        recommendations = await self.recommender.get_hybrid_recommendations(user_id, limit)
        return recommendations
    
    async def test_frequently_bought_together(self, product_id: str = None, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Test "frequently bought together" recommendations
        
        Args:
            product_id: Product ID to get recommendations for (random if None)
            limit: Maximum number of recommendations
            
        Returns:
            List of recommended products
        """
        # If no product ID provided, get a random one from the database
        if product_id is None:
            products = await self.db.products.distinct("id")
            if not products:
                print("No products found in database")
                return []
            product_id = random.choice(products)
        
        print(f"Getting frequently bought together recommendations for product {product_id}...")
        recommendations = await self.recommender.get_product_recommendations(product_id, limit)
        return recommendations
    
    def print_recommendations(self, recommendations: List[Dict[str, Any]], header: str = "Recommendations") -> None:
        """
        Pretty print recommendations
        
        Args:
            recommendations: List of recommended products
            header: Header for the table
        """
        if not recommendations:
            print("No recommendations found")
            return
        
        # Format data for tabulate
        table_data = []
        for i, rec in enumerate(recommendations, 1):
            product = rec.get("product", {})
            row = [
                i,
                rec.get("id", "N/A"),
                round(rec.get("score", 0), 2),
                product.get("title", "N/A"),
                product.get("brand", "N/A"),
                f"{product.get('priceCurrent', 0):.2f}",
                product.get("category", "N/A")
            ]
            table_data.append(row)
        
        # Print table
        headers = ["#", "Product ID", "Score", "Title", "Brand", "Price", "Category"]
        print(f"\n{header}")
        print(tabulate(table_data, headers=headers, tablefmt="grid"))


async def main():
    parser = argparse.ArgumentParser(description="Test the naive recommender system")
    parser.add_argument("--mongodb-uri", default="mongodb://localhost:27017/productdb", 
                        help="MongoDB URI")
    parser.add_argument("--products-file", default="../test_data/sample_recommendation_products.json", 
                        help="Path to products JSON file")
    parser.add_argument("--orders-file", default="../test_data/sample_recommendation_orderlines.json", 
                        help="Path to orderlines JSON file")
    parser.add_argument("--user-id", help="User ID for recommendations (random if not provided)")
    parser.add_argument("--product-id", help="Product ID for recommendations (random if not provided)")
    parser.add_argument("--limit", type=int, default=5, help="Maximum number of recommendations")
    parser.add_argument("--load-data", action="store_true", help="Load test data into database")
    parser.add_argument("--compute-pairs", action="store_true", help="Compute product pairs for recommendation")
    
    args = parser.parse_args()
    
    # Connect to MongoDB
    client = MongoClient(args.mongodb_uri)
    db_name = args.mongodb_uri.split("/")[-1]
    db = client[db_name]
    
    # Create tester
    tester = RecommenderTester(db)
    
    # Load test data if requested
    if args.load_data:
        products_path = os.path.abspath(args.products_file)
        orders_path = os.path.abspath(args.orders_file)
        
        if not os.path.exists(products_path):
            print(f"Products file not found: {products_path}")
            return
            
        if not os.path.exists(orders_path):
            print(f"Orders file not found: {orders_path}")
            return
            
        print(f"Loading test data from {products_path} and {orders_path}...")
        stats = await tester.setup_test_data(products_path, orders_path)
        print(f"Loaded {stats['products_count']} products and {stats['orderlines_count']} orderlines "
              f"for {stats['unique_customers']} customers")
    
    # Compute product pairs if requested
    if args.compute_pairs:
        result = await tester.compute_product_pairs()
        print(f"Computed {result['new_count']} product pairs")
    
    # Test all recommendation types
    try:
        # Test collaborative filtering
        collab_recs = await tester.test_collaborative_recommendations(args.user_id, args.limit)
        tester.print_recommendations(collab_recs, "Collaborative Filtering Recommendations")
        
        # Test content-based filtering
        content_recs = await tester.test_content_based_recommendations(args.product_id, args.limit)
        tester.print_recommendations(content_recs, "Content-Based Recommendations")
        
        # Test hybrid recommendations
        hybrid_recs = await tester.test_hybrid_recommendations(args.user_id, args.limit)
        tester.print_recommendations(hybrid_recs, "Hybrid Recommendations")
        
        # Test frequently bought together
        fbt_recs = await tester.test_frequently_bought_together(args.product_id, args.limit)
        tester.print_recommendations(fbt_recs, "Frequently Bought Together")
        
    except Exception as e:
        print(f"Error testing recommendations: {str(e)}")
    
    # Close MongoDB connection
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
