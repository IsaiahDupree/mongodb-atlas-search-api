"""
Test utilities for MongoDB Atlas Search API tests.

This module provides helpers to set up testing environments with proper mocking.
"""
import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List, Any, Optional, Generator, AsyncGenerator

# Add parent directory to path to enable proper imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Test constants
TEST_API_KEY = "test_api_key"
TEST_HEADERS = {"x-apikey": TEST_API_KEY}

# Sample test data that can be reused across tests
SAMPLE_PRODUCT = {
    "id": "test_prod1",
    "title": "Test Baby Shoes",
    "description": "Comfortable test shoes for babies",
    "brand": "TestBrand",
    "imageThumbnailUrl": "https://example.com/test.jpg",
    "priceOriginal": 199.99,
    "priceCurrent": 149.99,
    "isOnSale": True,
    "ageFrom": 1,
    "ageTo": 3,
    "ageBucket": "1 to 3 years",
    "color": "blue",
    "seasons": ["winter", "spring"],
    "productType": "main",
    "seasonRelevancyFactor": 0.8,
    "stockLevel": 45
}

SAMPLE_ORDERLINE = {
    "orderNr": "TEST-ORD123",
    "productNr": "test_prod1",
    "customerNr": "test_cust123",
    "seasonName": "winter",
    "dateTime": "2023-12-15T14:30:00"
}

# Mock class for MongoDB collections
class MockCollection:
    """Simple mock for MongoDB collections that tracks operations and returns predefined responses"""
    
    def __init__(self, name: str, data: List[Dict[str, Any]] = None):
        self.name = name
        self.data = data or []
        self.operations = []
    
    async def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Mock find_one operation"""
        self.operations.append(("find_one", query))
        
        if not self.data:
            return None
            
        # Simple implementation to find a matching document
        for doc in self.data:
            match = True
            for key, value in query.items():
                if key not in doc or doc[key] != value:
                    match = False
                    break
            if match:
                return doc
                
        return None
    
    def find(self, query: Dict[str, Any] = None) -> 'MockCursor':
        """Mock find operation"""
        query = query or {}
        self.operations.append(("find", query))
        
        # Return a mock cursor that will iterate through matching documents
        matching_docs = []
        for doc in self.data:
            match = True
            for key, value in (query or {}).items():
                if key not in doc or doc[key] != value:
                    match = False
                    break
            if match:
                matching_docs.append(doc)
                
        return MockCursor(matching_docs)
    
    async def insert_one(self, document: Dict[str, Any]) -> MagicMock:
        """Mock insert_one operation"""
        self.operations.append(("insert_one", document))
        self.data.append(document)
        result = MagicMock()
        result.inserted_id = document.get("id", "test_id")
        return result
    
    async def insert_many(self, documents: List[Dict[str, Any]]) -> MagicMock:
        """Mock insert_many operation"""
        self.operations.append(("insert_many", documents))
        self.data.extend(documents)
        result = MagicMock()
        result.inserted_ids = [doc.get("id", f"test_id_{i}") for i, doc in enumerate(documents)]
        return result
    
    async def delete_one(self, query: Dict[str, Any]) -> MagicMock:
        """Mock delete_one operation"""
        self.operations.append(("delete_one", query))
        
        # Remove the first matching document
        for i, doc in enumerate(self.data):
            match = True
            for key, value in query.items():
                if key not in doc or doc[key] != value:
                    match = False
                    break
            if match:
                del self.data[i]
                result = MagicMock()
                result.deleted_count = 1
                return result
        
        result = MagicMock()
        result.deleted_count = 0
        return result
    
    async def delete_many(self, query: Dict[str, Any]) -> MagicMock:
        """Mock delete_many operation"""
        self.operations.append(("delete_many", query))
        
        # Count and remove all matching documents
        deleted = 0
        i = 0
        while i < len(self.data):
            doc = self.data[i]
            match = True
            for key, value in (query or {}).items():
                if key not in doc or doc[key] != value:
                    match = False
                    break
            if match:
                del self.data[i]
                deleted += 1
            else:
                i += 1
        
        result = MagicMock()
        result.deleted_count = deleted
        return result
    
    async def distinct(self, field: str, query: Dict[str, Any] = None) -> List[Any]:
        """Mock distinct operation"""
        self.operations.append(("distinct", field, query))
        
        # Get distinct values for the field
        values = set()
        for doc in self.data:
            if field in doc:
                values.add(doc[field])
                
        return list(values)
    
    def aggregate(self, pipeline: List[Dict[str, Any]]) -> 'MockCursor':
        """Mock aggregate operation"""
        self.operations.append(("aggregate", pipeline))
        
        # For testing we'll just return the raw data
        # In a more sophisticated mock, we could implement pipeline operations
        return MockCursor(self.data)
    
    async def count_documents(self, query: Dict[str, Any] = None) -> int:
        """Mock count_documents operation"""
        self.operations.append(("count_documents", query))
        
        # Count matching documents
        count = 0
        for doc in self.data:
            match = True
            for key, value in (query or {}).items():
                if key not in doc or doc[key] != value:
                    match = False
                    break
            if match:
                count += 1
                
        return count
    
    async def replace_one(self, filter_query: Dict[str, Any], 
                          replacement: Dict[str, Any], 
                          upsert: bool = False) -> MagicMock:
        """Mock replace_one operation"""
        self.operations.append(("replace_one", filter_query, replacement, upsert))
        
        # Try to find and replace a document
        for i, doc in enumerate(self.data):
            match = True
            for key, value in filter_query.items():
                if key not in doc or doc[key] != value:
                    match = False
                    break
            if match:
                self.data[i] = replacement
                result = MagicMock()
                result.modified_count = 1
                result.upserted_id = None
                return result
        
        # If not found and upsert is True, insert
        if upsert:
            self.data.append(replacement)
            result = MagicMock()
            result.modified_count = 0
            result.upserted_id = replacement.get("id", "test_id")
            return result
        
        # Not found and no upsert
        result = MagicMock()
        result.modified_count = 0
        result.upserted_id = None
        return result


class MockCursor:
    """Mock MongoDB cursor that yields documents"""
    
    def __init__(self, documents: List[Dict[str, Any]]):
        self.documents = documents
        self.current_index = 0
    
    def __aiter__(self):
        return self
    
    async def __anext__(self):
        if self.current_index >= len(self.documents):
            raise StopAsyncIteration
        
        result = self.documents[self.current_index]
        self.current_index += 1
        return result
    
    async def to_list(self, length: Optional[int] = None) -> List[Dict[str, Any]]:
        """Convert cursor to a list of documents"""
        if length is None or length >= len(self.documents):
            return self.documents
        return self.documents[:length]


class MockDatabase:
    """Mock MongoDB database"""
    
    def __init__(self):
        self.collections = {}
        
        # Initialize with some common collections
        self.collections["products"] = MockCollection("products")
        self.collections["orderlines"] = MockCollection("orderlines")
        self.collections["product_pairs"] = MockCollection("product_pairs")
    
    def __getattr__(self, name: str) -> MockCollection:
        """Support attribute access (db.collection)"""
        if name not in self.collections:
            self.collections[name] = MockCollection(name)
        return self.collections[name]
    
    def collection_names(self) -> List[str]:
        """Get all collection names"""
        return list(self.collections.keys())
    
    async def list_collection_names(self) -> List[str]:
        """Get all collection names (async version)"""
        return list(self.collections.keys())
    
    async def command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Mock database command"""
        return {"ok": 1}
    
    def get_collection(self, name: str) -> MockCollection:
        """Get a collection by name"""
        if name not in self.collections:
            self.collections[name] = MockCollection(name)
        return self.collections[name]


def get_test_patches() -> List[patch]:
    """Get patches for testing"""
    # Create mock database
    mock_db = MockDatabase()
    
    # Add sample products
    mock_db.products.data = [
        SAMPLE_PRODUCT,
        {
            "id": "test_prod2",
            "title": "Baby Winter Hat Blue",
            "description": "Warm winter hat for babies",
            "brand": "TestBrand",
            "priceOriginal": 99.99,
            "priceCurrent": 89.99,
            "color": "blue",
            "seasons": ["winter"]
        }
    ]
    
    # Add sample orderlines
    mock_db.orderlines.data = [SAMPLE_ORDERLINE]
    
    # Create patches
    patches = [
        patch("dependencies.API_KEY", TEST_API_KEY),
        patch("database.mongodb.get_db", AsyncMock(return_value=mock_db)),
        patch("database.mongodb.get_product_collection", AsyncMock(return_value=mock_db.products)),
        patch("database.mongodb.get_orderlines_collection", AsyncMock(return_value=mock_db.orderlines)),
        patch("database.mongodb.get_product_pairs_collection", AsyncMock(return_value=mock_db.product_pairs)),
        patch("services.embedding.embedding_service.generate_embedding", MagicMock(return_value=[0.1] * 384))
    ]
    
    return patches


async def apply_patches(patches: List[patch]) -> Generator:
    """Apply multiple patches at once and yield them"""
    patchers = []
    for p in patches:
        patchers.append(p.start())
    
    yield patchers
    
    for p in patches:
        p.stop()


def init_test_data(db: MockDatabase) -> None:
    """Initialize test data in mock database"""
    # Add sample products if not already present
    if not db.products.data:
        db.products.data = [
            SAMPLE_PRODUCT,
            {
                "id": "test_prod2",
                "title": "Baby Winter Hat Blue",
                "description": "Warm winter hat for babies",
                "brand": "TestBrand",
                "priceOriginal": 99.99,
                "priceCurrent": 89.99,
                "color": "blue",
                "seasons": ["winter"]
            }
        ]
    
    # Add sample orderlines if not already present
    if not db.orderlines.data:
        db.orderlines.data = [SAMPLE_ORDERLINE]
