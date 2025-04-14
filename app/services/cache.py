"""
Caching service for improving performance of frequently executed queries.
Uses a simple in-memory LRU cache with TTL (time-to-live) functionality.
"""

import time
import threading
from collections import OrderedDict
import hashlib
import json
from typing import Any, Dict, Optional, Tuple

class LRUCache:
    """
    Simple thread-safe LRU (Least Recently Used) cache implementation
    with time-to-live (TTL) support for cached items.
    """
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        """
        Initialize the LRU cache.
        
        Args:
            max_size: Maximum number of items to store in the cache
            ttl_seconds: Time-to-live for cached items in seconds
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache = OrderedDict()  # {key: (value, timestamp)}
        self.lock = threading.RLock()  # Reentrant lock for thread safety
    
    def _generate_key(self, data: Any) -> str:
        """Generate a consistent hash key for any data type"""
        if isinstance(data, dict):
            # Sort dictionary to ensure consistent hashing regardless of key order
            serialized = json.dumps(data, sort_keys=True)
        elif isinstance(data, (list, tuple)):
            # Handle lists and tuples
            serialized = json.dumps(data)
        elif isinstance(data, (str, int, float, bool)):
            # Handle primitive types
            serialized = str(data)
        else:
            # For other types, use string representation
            serialized = str(data)
            
        return hashlib.md5(serialized.encode()).hexdigest()
    
    def get(self, key: Any) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: The key to look up
            
        Returns:
            The cached value or None if not found or expired
        """
        hash_key = self._generate_key(key)
        
        with self.lock:
            if hash_key not in self.cache:
                return None
                
            value, timestamp = self.cache[hash_key]
            
            # Check if the item has expired
            if time.time() - timestamp > self.ttl_seconds:
                # Remove expired item
                del self.cache[hash_key]
                return None
                
            # Move item to the end to indicate it was recently accessed
            self.cache.move_to_end(hash_key)
            return value
    
    def set(self, key: Any, value: Any) -> None:
        """
        Add or update an item in the cache.
        
        Args:
            key: The key to store
            value: The value to cache
        """
        hash_key = self._generate_key(key)
        
        with self.lock:
            # Add/update the item
            self.cache[hash_key] = (value, time.time())
            
            # Move to end to indicate it was recently accessed
            self.cache.move_to_end(hash_key)
            
            # Remove oldest items if cache is too large
            while len(self.cache) > self.max_size:
                self.cache.popitem(last=False)
    
    def clear(self) -> None:
        """Clear all cached items"""
        with self.lock:
            self.cache.clear()
    
    def remove(self, key: Any) -> None:
        """Remove a specific item from the cache"""
        hash_key = self._generate_key(key)
        
        with self.lock:
            if hash_key in self.cache:
                del self.cache[hash_key]
    
    def remove_pattern(self, pattern: str) -> int:
        """
        Remove all items with keys containing the pattern.
        
        Returns:
            Number of items removed
        """
        removed_count = 0
        
        with self.lock:
            # Get keys to remove (can't modify during iteration)
            keys_to_remove = [k for k in self.cache.keys() if pattern in k]
            
            # Remove matching keys
            for k in keys_to_remove:
                del self.cache[k]
                removed_count += 1
                
        return removed_count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "ttl_seconds": self.ttl_seconds
            }

# Global cache instances
# Different caches for different types of data with appropriate sizes and TTL values
search_cache = LRUCache(max_size=500, ttl_seconds=300)  # 5 minutes for search results
product_cache = LRUCache(max_size=1000, ttl_seconds=3600)  # 1 hour for product details
recommendations_cache = LRUCache(max_size=200, ttl_seconds=1800)  # 30 minutes for recommendations
