"""
Advanced recommendation algorithms for product recommendation functionality.
Implements various recommendation strategies:
1. Co-occurrence based (users who bought X also bought Y)
2. Embedding similarity based (content-based recommendations)
3. Seasonal relevancy boosting
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pymongo.collection import Collection

from services.embedding import embedding_service
from services.cache import recommendations_cache

class RecommendationEngine:
    """
    Recommendation engine that combines multiple recommendation strategies
    to provide high-quality product recommendations
    """
    
    @staticmethod
    async def get_co_occurrence_recommendations(
        product_id: str, 
        orderlines_collection: Collection,
        product_collection: Collection,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get recommendations based on co-occurrence patterns in order data
        (users who bought X also bought Y)
        
        Args:
            product_id: The ID of the product to get recommendations for
            orderlines_collection: MongoDB collection for orderlines
            product_collection: MongoDB collection for products
            limit: Maximum number of recommendations to return
            
        Returns:
            List of recommended products
        """
        # Check cache first
        cache_key = f"co_occurrence:{product_id}:{limit}"
        cached_result = recommendations_cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # Find orders containing this product
        orders_with_product = await orderlines_collection.find(
            {"productNr": product_id}
        ).distinct("orderNr")
        
        if not orders_with_product:
            return []
        
        # Find other products purchased in the same orders (excluding the input product)
        pipeline = [
            # Match orderlines in the same orders
            {"$match": {"orderNr": {"$in": orders_with_product}, "productNr": {"$ne": product_id}}},
            # Group by product and count occurrences
            {"$group": {"_id": "$productNr", "count": {"$sum": 1}}},
            # Sort by count descending
            {"$sort": {"count": -1}},
            # Limit number of recommendations
            {"$limit": limit}
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
        
        # Cache results
        recommendations_cache.set(cache_key, recommended_products)
        
        return recommended_products
    
    @staticmethod
    async def get_embedding_similarity_recommendations(
        product_id: str,
        product_collection: Collection,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get recommendations based on embedding similarity (content-based)
        
        Args:
            product_id: The ID of the product to get recommendations for
            product_collection: MongoDB collection for products
            limit: Maximum number of recommendations to return
            
        Returns:
            List of recommended products based on content similarity
        """
        # Check cache first
        cache_key = f"embedding_similarity:{product_id}:{limit}"
        cached_result = recommendations_cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # Get source product
        source_product = await product_collection.find_one({"id": product_id})
        if not source_product:
            return []
            
        # Extract embeddings from source product
        title_embedding = source_product.get("title_embedding")
        description_embedding = source_product.get("description_embedding")
        
        if not title_embedding or not description_embedding:
            return []
        
        # Find similar products using vector search
        pipeline = [
            {
                "$search": {
                    "index": "product_search",
                    "knnBeta": {
                        "vector": title_embedding,
                        "path": "title_embedding",
                        "k": limit + 1,  # +1 because we'll exclude the source product
                    }
                }
            },
            {"$match": {"id": {"$ne": product_id}}},  # Exclude the source product
            {"$limit": limit}
        ]
        
        similar_products = []
        cursor = product_collection.aggregate(pipeline)
        async for product in cursor:
            # Remove MongoDB _id and embedding vectors from response
            if "_id" in product:
                del product["_id"]
            if "title_embedding" in product:
                del product["title_embedding"]
            if "description_embedding" in product:
                del product["description_embedding"]
            similar_products.append(product)
        
        # Cache results
        recommendations_cache.set(cache_key, similar_products)
        
        return similar_products
    
    @staticmethod
    def boost_by_season(
        products: List[Dict[str, Any]], 
        current_season: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Boost products by seasonal relevance
        
        Args:
            products: List of products to boost
            current_season: Current season (spring, summer, autumn, winter)
                           If None, determine based on current date
                           
        Returns:
            Reordered product list with seasonal products boosted
        """
        if not products:
            return []
            
        # Determine current season if not provided
        if current_season is None:
            month = datetime.now().month
            if 3 <= month <= 5:
                current_season = "spring"
            elif 6 <= month <= 8:
                current_season = "summer"
            elif 9 <= month <= 11:
                current_season = "autumn"
            else:
                current_season = "winter"
        
        # Calculate a seasonal boost for each product
        scored_products = []
        for product in products:
            # Base score starts at 1
            score = 1.0
            
            # Boost products that match the current season
            if "seasons" in product and product["seasons"]:
                # If product is relevant for the current season, boost it
                if current_season in product["seasons"] or "all" in product["seasons"]:
                    # Use seasonRelevancyFactor if available
                    if "seasonRelevancyFactor" in product:
                        score += product["seasonRelevancyFactor"]
                    else:
                        score += 0.5  # Default boost
                        
            # Boost in-stock products
            if "stockLevel" in product and product["stockLevel"] > 0:
                score += 0.3
                
            # Apply additional boost for products on sale
            if "isOnSale" in product and product["isOnSale"]:
                score += 0.2
                
            scored_products.append((product, score))
        
        # Sort by score descending
        scored_products.sort(key=lambda x: x[1], reverse=True)
        
        # Return just the products in the new order
        return [product for product, _ in scored_products]
    
    @staticmethod
    async def get_hybrid_recommendations(
        product_id: str,
        orderlines_collection: Collection,
        product_collection: Collection,
        limit: int = 5,
        current_season: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get hybrid recommendations combining co-occurrence and content-based approaches
        with seasonal boosting
        
        Args:
            product_id: The ID of the product to get recommendations for
            orderlines_collection: MongoDB collection for orderlines
            product_collection: MongoDB collection for products
            limit: Maximum number of recommendations to return
            current_season: Current season for seasonal boosting
            
        Returns:
            List of recommended products using hybrid approach
        """
        # Check cache first
        cache_key = f"hybrid:{product_id}:{limit}:{current_season or 'auto'}"
        cached_result = recommendations_cache.get(cache_key)
        if cached_result:
            return cached_result
            
        # Get recommendations from both approaches
        co_occurrence_recs = await RecommendationEngine.get_co_occurrence_recommendations(
            product_id, orderlines_collection, product_collection, limit=limit
        )
        
        embedding_recs = await RecommendationEngine.get_embedding_similarity_recommendations(
            product_id, product_collection, limit=limit
        )
        
        # Merge recommendations, prioritizing co-occurrence but ensuring diversity
        product_ids_seen = set()
        hybrid_recs = []
        
        # First, add co-occurrence recommendations (behavior-based)
        for product in co_occurrence_recs:
            if product["id"] not in product_ids_seen:
                product_ids_seen.add(product["id"])
                hybrid_recs.append(product)
        
        # Then add embedding-based recommendations not already included
        for product in embedding_recs:
            if product["id"] not in product_ids_seen and len(hybrid_recs) < limit * 2:
                product_ids_seen.add(product["id"])
                hybrid_recs.append(product)
        
        # Apply seasonal boosting
        boosted_recs = RecommendationEngine.boost_by_season(hybrid_recs, current_season)
        
        # Trim to requested limit
        final_recs = boosted_recs[:limit]
        
        # Cache the result
        recommendations_cache.set(cache_key, final_recs)
        
        return final_recs
