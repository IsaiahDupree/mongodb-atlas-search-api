"""
Naive product recommender system using MongoDB and Atlas Search.
Implements both collaborative filtering (frequently bought together)
and content-based recommendation approaches.
"""

from typing import List, Dict, Any, Optional
from pymongo.database import Database
from pymongo.collection import Collection
import asyncio

class NaiveRecommender:
    """
    Implementation of a naive product recommendation system
    using MongoDB aggregation pipelines and Atlas Search.
    """
    
    def __init__(self, db: Database):
        """
        Initialize the recommender with MongoDB database instance
        
        Args:
            db: MongoDB database instance
        """
        self.db = db
        self.products_collection = db.products
        self.orders_collection = db.orderlines
        
        # Collection to store pre-computed product pairs
        self.product_pairs_collection = db.product_pairs
    
    async def pre_compute_product_pairs(self) -> Dict[str, Any]:
        """
        Pre-compute product pairs that are frequently bought together.
        This is an expensive operation that should be run periodically,
        not on each recommendation request.
        
        Returns:
            Statistics about the computation
        """
        start_count = await self.product_pairs_collection.count_documents({})
        
        # Clear existing pairs
        await self.product_pairs_collection.delete_many({})
        
        # Aggregation pipeline to find product pairs
        pipeline = [
            # Unwind order lines to get individual product purchases
            {"$unwind": "$orderLines"},
            
            # Group by order ID to identify products bought together
            {"$group": {
                "_id": "$orderNr",
                "products": {"$push": "$orderLines.productNr"},
                "userId": {"$first": "$customerNr"}
                }
            },
            
            # Filter orders with at least 2 products
            {"$match": {"products.1": {"$exists": True}}},
            
            # Unwind products to create pairs
            {"$unwind": "$products"},
            
            # Create pairs with other products in same order
            {"$unwind": {
                "path": "$products",
                "includeArrayIndex": "position"
                }
            },
            
            # Group by product pairs to count co-occurrences
            {"$group": {
                "_id": {
                    "product1": {"$min": ["$products", "$products"]},
                    "product2": {"$max": ["$products", "$products"]}
                },
                "count": {"$sum": 1}
                }
            },
            
            # Filter out self-pairs
            {"$match": {"$expr": {"$ne": ["$_id.product1", "$_id.product2"]}}},
            
            # Sort by frequency
            {"$sort": {"count": -1}}
        ]
        
        # Execute the pipeline
        product_pairs = await self.orders_collection.aggregate(pipeline).to_list(None)
        
        # Insert the results into the product_pairs collection
        if product_pairs:
            await self.product_pairs_collection.insert_many(product_pairs)
        
        # Get final count
        end_count = await self.product_pairs_collection.count_documents({})
        
        return {
            "previous_count": start_count,
            "new_count": end_count,
            "pairs_computed": end_count
        }
    
    async def get_collaborative_recommendations(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get personalized recommendations based on user purchase history (collaborative filtering)
        
        Args:
            user_id: User ID to get recommendations for
            limit: Maximum number of recommendations to return
            
        Returns:
            List of recommended products
        """
        pipeline = [
            # Match orders from this user
            {"$match": {"customerNr": user_id}},
            
            # Unwind order lines
            {"$unwind": "$orderLines"},
            
            # Get the products this user has purchased
            {"$group": {
                "_id": user_id,
                "purchasedProducts": {"$addToSet": "$orderLines.productNr"}
                }
            },
            
            # Lookup products frequently bought with these products
            {"$lookup": {
                "from": "product_pairs",
                "localField": "purchasedProducts",
                "foreignField": "_id.product1",
                "as": "recommendations"
                }
            },
            
            # Unwind recommendations
            {"$unwind": "$recommendations"},
            
            # Filter out products user already has
            {"$match": {
                "$expr": {
                    "$not": {"$in": ["$recommendations._id.product2", "$purchasedProducts"]}
                    }
                }
            },
            
            # Group and sum scores for each recommended product
            {"$group": {
                "_id": "$recommendations._id.product2",
                "score": {"$sum": "$recommendations.count"}
                }
            },
            
            # Sort by recommendation score
            {"$sort": {"score": -1}},
            
            # Limit results
            {"$limit": limit},
            
            # Lookup product details
            {"$lookup": {
                "from": "products",
                "localField": "_id",
                "foreignField": "id",
                "as": "productDetails"
                }
            },
            
            {"$unwind": "$productDetails"}
        ]
        
        # Execute the pipeline
        recommendations = await self.orders_collection.aggregate(pipeline).to_list(None)
        
        # Format the output
        return [
            {
                "id": rec["_id"],
                "score": rec["score"],
                "product": rec["productDetails"]
            }
            for rec in recommendations
        ]
    
    async def get_content_based_recommendations(self, product_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get content-based recommendations based on a product
        
        Args:
            product_id: Product ID to get recommendations for
            limit: Maximum number of recommendations to return
            
        Returns:
            List of recommended products
        """
        # First get the product details
        product = await self.products_collection.find_one({"id": product_id})
        if not product:
            return []
        
        # Use Atlas Search to find similar products
        pipeline = [
            {
                "$search": {
                    "compound": {
                        "should": [
                            {
                                "text": {
                                    "query": product["title"],
                                    "path": "title",
                                    "score": {"boost": {"value": 3}}
                                }
                            },
                            {
                                "text": {
                                    "query": product["description"],
                                    "path": "description",
                                    "score": {"boost": {"value": 2}}
                                }
                            },
                            {
                                "equals": {
                                    "path": "brand",  # Using brand instead of category
                                    "value": product["brand"],
                                    "score": {"boost": {"value": 5}}
                                }
                            }
                        ]
                    }
                }
            },
            # Exclude the original product
            {"$match": {"id": {"$ne": product_id}}},
            # Limit results
            {"$limit": limit}
        ]
        
        # Execute the pipeline
        similar_products = await self.products_collection.aggregate(pipeline).to_list(None)
        
        # Format the output
        return [
            {
                "id": product["id"],
                "score": 1.0,  # Default score since Atlas Search doesn't return scores easily
                "product": product
            }
            for product in similar_products
        ]
    
    async def get_hybrid_recommendations(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get hybrid recommendations combining collaborative filtering and content-based approaches
        
        Args:
            user_id: User ID to get recommendations for
            limit: Maximum number of recommendations to return
            
        Returns:
            List of recommended products
        """
        # Get collaborative filtering recommendations
        collaborative_recs = await self.get_collaborative_recommendations(user_id, limit)
        
        # Get the user's most recent purchases
        recent_purchases_pipeline = [
            {"$match": {"customerNr": user_id}},
            {"$sort": {"dateTime": -1}},
            {"$limit": 1},
            {"$unwind": "$orderLines"},
            {"$project": {"productId": "$orderLines.productNr", "_id": 0}}
        ]
        
        recent_purchases = await self.orders_collection.aggregate(recent_purchases_pipeline).to_list(None)
        
        # Get content-based recommendations for recent purchases
        content_based_recs = []
        for purchase in recent_purchases:
            product_id = purchase.get("productId")
            if product_id:
                recs = await self.get_content_based_recommendations(product_id, limit=5)
                content_based_recs.extend(recs)
        
        # Combine and deduplicate recommendations
        all_recs = collaborative_recs + content_based_recs
        deduped_recs = []
        seen_ids = set()
        
        for rec in all_recs:
            if rec["id"] not in seen_ids:
                seen_ids.add(rec["id"])
                deduped_recs.append(rec)
        
        # Sort by score
        sorted_recs = sorted(deduped_recs, key=lambda x: x["score"], reverse=True)
        
        # Return top recommendations
        return sorted_recs[:limit]
    
    async def get_product_recommendations(self, product_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get recommendations based on a specific product (frequently bought together)
        
        Args:
            product_id: Product ID to get recommendations for
            limit: Maximum number of recommendations to return
            
        Returns:
            List of recommended products
        """
        pipeline = [
            # Get product pairs where this product is product1
            {"$match": {"_id.product1": product_id}},
            
            # Sort by frequency
            {"$sort": {"count": -1}},
            
            # Limit results
            {"$limit": limit},
            
            # Lookup product details
            {"$lookup": {
                "from": "products",
                "localField": "_id.product2",
                "foreignField": "id",
                "as": "productDetails"
                }
            },
            
            {"$unwind": "$productDetails"}
        ]
        
        # Execute the pipeline
        recommendations1 = await self.product_pairs_collection.aggregate(pipeline).to_list(None)
        
        # Also check pairs where this product is product2
        pipeline = [
            # Get product pairs where this product is product2
            {"$match": {"_id.product2": product_id}},
            
            # Sort by frequency
            {"$sort": {"count": -1}},
            
            # Limit results
            {"$limit": limit},
            
            # Lookup product details
            {"$lookup": {
                "from": "products",
                "localField": "_id.product1",
                "foreignField": "id",
                "as": "productDetails"
                }
            },
            
            {"$unwind": "$productDetails"}
        ]
        
        # Execute the pipeline
        recommendations2 = await self.product_pairs_collection.aggregate(pipeline).to_list(None)
        
        # Combine recommendations
        all_recs = recommendations1 + recommendations2
        
        # Sort by count and deduplicate
        sorted_recs = sorted(all_recs, key=lambda x: x["count"], reverse=True)
        deduped_recs = []
        seen_ids = set()
        
        for rec in sorted_recs:
            product_id = rec["productDetails"]["id"]
            if product_id not in seen_ids:
                seen_ids.add(product_id)
                deduped_recs.append({
                    "id": product_id,
                    "score": rec["count"],
                    "product": rec["productDetails"]
                })
        
        # Return top recommendations
        return deduped_recs[:limit]
