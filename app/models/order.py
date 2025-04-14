from typing import Optional
from datetime import datetime
from pydantic import BaseModel

class OrderLine(BaseModel):
    """
    OrderLine data model as per requirements (Obj4)
    Contains data about product purchases to use for recommendations
    """
    orderNr: str
    productNr: str
    customerNr: str
    seasonName: str
    dateTime: datetime
    
    class Config:
        schema_extra = {
            "example": {
                "orderNr": "ORD12345",
                "productNr": "prod1",
                "customerNr": "cust789",
                "seasonName": "winter",
                "dateTime": "2023-12-15T14:30:00"
            }
        }

class RecommendationQuery(BaseModel):
    """
    Query model for product recommendations
    """
    productId: str
    limit: int = 5
    
    class Config:
        schema_extra = {
            "example": {
                "productId": "prod1",
                "limit": 5
            }
        }
