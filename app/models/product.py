from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class Product(BaseModel):
    """
    Product data model as per requirements
    """
    id: str
    title: str
    description: str
    brand: str
    imageThumbnailUrl: str = ""
    priceOriginal: float
    priceCurrent: float
    isOnSale: bool = False
    ageFrom: Optional[int] = None
    ageTo: Optional[int] = None
    ageBucket: Optional[str] = None  # e.g., "1 to 3 years"
    color: Optional[str] = None
    seasons: Optional[List[str]] = None  # e.g., ["winter", "spring"]
    productType: str = "main"  # main, part, extras
    seasonRelevancyFactor: float = 0.5  # 0 to 1 for boosting
    stockLevel: int = 0
    
    # Fields for vector search (populated during ingestion)
    title_embedding: Optional[List[float]] = None
    description_embedding: Optional[List[float]] = None
    
    class Config:
        schema_extra = {
            "example": {
                "id": "prod1",
                "title": "Baby Shoes",
                "description": "Comfortable shoes for babies",
                "brand": "BabySteps",
                "imageThumbnailUrl": "https://example.com/image.jpg",
                "priceOriginal": 299.99,
                "priceCurrent": 249.99,
                "isOnSale": True,
                "ageFrom": 1,
                "ageTo": 3,
                "ageBucket": "1 to 3 years",
                "color": "red",
                "seasons": ["winter", "spring"],
                "productType": "main",
                "seasonRelevancyFactor": 0.8,
                "stockLevel": 45
            }
        }

class ProductInDB(Product):
    """
    Product model with additional database fields
    """
    title_embedding: Optional[List[float]] = None
    description_embedding: Optional[List[float]] = None
    _id: Optional[str] = None

class ProductSearchQuery(BaseModel):
    """
    Model for product search queries
    """
    query: str
    filters: Optional[Dict[str, Any]] = None
    limit: int = 10
    offset: int = 0
    
    class Config:
        schema_extra = {
            "example": {
                "query": "red baby shoes",
                "filters": {
                    "ageBucket": "1 to 3 years",
                    "brand": "BabySteps",
                    "isOnSale": True
                },
                "limit": 10,
                "offset": 0
            }
        }

class AutosuggestQuery(BaseModel):
    """
    Model for autosuggest/autocomplete queries
    """
    prefix: str
    limit: int = 5
    
    class Config:
        schema_extra = {
            "example": {
                "prefix": "bab",
                "limit": 5
            }
        }

class FacetResult(BaseModel):
    """
    Facet result for filtering search results
    """
    field: str
    values: List[Dict[str, Any]]

class SearchResult(BaseModel):
    """
    Search result model with facets
    """
    total: int
    products: List[Product]
    facets: Optional[List[FacetResult]] = None
    query_explanation: Optional[Dict[str, Any]] = None
