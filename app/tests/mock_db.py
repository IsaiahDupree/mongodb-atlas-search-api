"""
Mock MongoDB database for testing
This module provides mock MongoDB objects that can be used in tests
instead of real database connections.
"""
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List, Any, Optional


class MockCollection:
    """Mock MongoDB collection with async methods"""
    
    def __init__(self, collection_name: str, data: Optional[List[Dict[str, Any]]] = None):
        self.name = collection_name
        self.data = data or []
        self._setup_methods()
    
    def _setup_methods(self):
        """Set up common collection methods"""
        # Find one
        self.find_one = AsyncMock()
        self.find_one.return_value = self.data[0] if self.data else None
        
        # Find
        self.find = MagicMock()
        cursor_mock = AsyncMock()
        cursor_mock.__aiter__.return_value = self.data
        self.find.return_value = cursor_mock
        
        # Insert one
        self.insert_one = AsyncMock()
        self.insert_one.return_value = MagicMock(inserted_id="test_id")
        
        # Insert many
        self.insert_many = AsyncMock()
        self.insert_many.return_value = MagicMock(inserted_ids=["test_id1", "test_id2"])
        
        # Delete one
        self.delete_one = AsyncMock()
        self.delete_one.return_value = MagicMock(deleted_count=1)
        
        # Delete many
        self.delete_many = AsyncMock()
        self.delete_many.return_value = MagicMock(deleted_count=len(self.data))
        
        # Aggregate
        self.aggregate = MagicMock()
        agg_cursor_mock = AsyncMock()
        agg_cursor_mock.__aiter__.return_value = self.data
        agg_cursor_mock.to_list = AsyncMock(return_value=self.data)
        self.aggregate.return_value = agg_cursor_mock
        
        # Distinct
        self.distinct = AsyncMock()
        self.distinct.return_value = list(set(d.get("id", i) for i, d in enumerate(self.data)))
        
        # Replace one
        self.replace_one = AsyncMock()
        self.replace_one.return_value = MagicMock(upserted_id="test_id")
        
        # Update one
        self.update_one = AsyncMock()
        self.update_one.return_value = MagicMock(modified_count=1)


class MockDatabase:
    """Mock MongoDB database with collections"""
    
    def __init__(self):
        self.collections = {}
        self.command = AsyncMock()
        self.command.return_value = {"ok": 1}
    
    def add_collection(self, name: str, data: Optional[List[Dict[str, Any]]] = None):
        """Add a collection to the mock database"""
        self.collections[name] = MockCollection(name, data)
        # Add collection as attribute for natural db.collection access
        setattr(self, name, self.collections[name])
    
    def __getitem__(self, name: str):
        """Support dict-style access db['collection']"""
        if name not in self.collections:
            self.add_collection(name)
        return self.collections[name]
    
    async def list_collection_names(self):
        """Return all collection names"""
        return list(self.collections.keys())


class MockClient:
    """Mock MongoDB client"""
    
    def __init__(self):
        self.databases = {}
        self.default_db = MockDatabase()
        self.admin = MockDatabase()
        self.admin.command = AsyncMock(return_value={"ok": 1, "version": "5.0.0"})
    
    def get_database(self, name: Optional[str] = None):
        """Get a database by name"""
        if name is None:
            return self.default_db
        
        if name not in self.databases:
            self.databases[name] = MockDatabase()
        
        return self.databases[name]
    
    def __getitem__(self, name: str):
        """Support dict-style access client['database']"""
        return self.get_database(name)
    
    def close(self):
        """Mock close connection"""
        pass


def get_mock_db_patch():
    """Create a patch for the main db module"""
    mock_client = MockClient()
    mock_db = mock_client.get_database()
    
    # Add standard collections
    mock_db.add_collection("products", [
        {"id": "test_prod1", "title": "Test Product 1", "brand": "TestBrand"},
        {"id": "test_prod2", "title": "Test Product 2", "brand": "AnotherBrand"}
    ])
    
    mock_db.add_collection("orderlines", [
        {"orderNr": "order1", "productNr": "test_prod1", "customerNr": "cust1"},
        {"orderNr": "order1", "productNr": "test_prod2", "customerNr": "cust1"}
    ])
    
    mock_db.add_collection("product_pairs", [
        {"product1": "test_prod1", "product2": "test_prod2", "score": 0.85}
    ])
    
    # Create the patch objects
    patches = [
        patch("database.mongodb.db.client", mock_client),
        patch("database.mongodb.db.db", mock_db),
        patch("database.mongodb.get_db", return_value=mock_db)
    ]
    
    return patches
