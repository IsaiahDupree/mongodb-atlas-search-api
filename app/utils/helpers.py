import json
import logging
from typing import Dict, Any, List, Optional
from fastapi import HTTPException, status

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def format_search_response(
    products: List[Dict[str, Any]], 
    facets: Optional[List[Dict[str, Any]]] = None,
    total_count: int = 0
) -> Dict[str, Any]:
    """
    Format search results with consistent structure
    """
    return {
        "total": total_count,
        "products": products,
        "facets": facets or []
    }

def handle_search_error(error: Exception) -> None:
    """
    Handle search-related errors consistently
    """
    logger.error(f"Search error: {str(error)}")
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Search operation failed: {str(error)}"
    )

def sanitize_product(product: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove sensitive or internal fields from product before returning to client
    """
    # Create a copy to avoid modifying the original
    sanitized = product.copy()
    
    # Remove MongoDB _id field
    if "_id" in sanitized:
        del sanitized["_id"]
        
    # Remove embedding vectors (they're large and not needed by clients)
    if "title_embedding" in sanitized:
        del sanitized["title_embedding"]
    if "description_embedding" in sanitized:
        del sanitized["description_embedding"]
        
    return sanitized

def sanitize_products(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sanitize a list of products
    """
    return [sanitize_product(p) for p in products]

def log_api_request(endpoint: str, request_data: Any) -> None:
    """
    Log API requests for monitoring and debugging
    """
    logger.info(f"API Request - {endpoint}: {json.dumps(request_data, default=str)[:200]}...")

def log_search_query(query: str, filters: Dict[str, Any] = None) -> None:
    """
    Log search queries for future analysis and improvements
    """
    logger.info(f"Search Query: '{query}' - Filters: {json.dumps(filters or {})}")
