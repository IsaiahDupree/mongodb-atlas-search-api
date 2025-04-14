from fastapi import Header, HTTPException, status
import os

API_KEY = os.getenv("API_KEY", "your_default_api_key")

async def get_api_key(x_apikey: str = Header(...)):
    """
    Validate the API key sent in the x-apikey header.
    As per requirement Obj5, this is a simple shared secret validation.
    """
    if x_apikey != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return x_apikey
