#!/usr/bin/env python
"""
Product Data Transformation Script

This script transforms product data from the Omnium format to the format expected
by the MongoDB Atlas Search API.

Usage:
    python transform_data.py --input <input_file> --output <output_file> [--limit <limit>]

Arguments:
    --input     Path to the input JSON file (Omnium format)
    --output    Path to the output JSON file (MongoDB format)
    --limit     Optional: Maximum number of products to process
"""

import argparse
import json
import logging
import sys
from typing import Dict, List, Any, Optional, Set
import re
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("data_transform")

# Constants
DEFAULT_SEASON_RELEVANCY = 0.5
DEFAULT_PRODUCT_TYPE = "main"


def extract_property_value(product: Dict[str, Any], key: str, 
                           group: Optional[str] = None) -> Optional[str]:
    """
    Extract a value from the properties array based on the key and optional group.
    
    Args:
        product: The product dictionary
        key: The property key to search for
        group: Optional group to filter by
        
    Returns:
        The property value or None if not found
    """
    if "properties" not in product:
        return None
        
    for prop in product["properties"]:
        if prop["key"] == key:
            if group is None or ("keyGroup" in prop and prop["keyGroup"] == group):
                return prop["value"]
    return None


def extract_brand(product: Dict[str, Any]) -> str:
    """
    Extract the brand name from the product.
    
    Args:
        product: The product dictionary
        
    Returns:
        The brand name or "Unknown Brand" if not found
    """
    # First try the supplierName field
    if "supplierName" in product and product["supplierName"]:
        return product["supplierName"]
    
    # Try to find brand in properties
    brand = extract_property_value(product, "Brand") or \
            extract_property_value(product, "brand")
    
    return brand or "Unknown Brand"


def extract_description(product: Dict[str, Any]) -> str:
    """
    Generate a description from available product data.
    
    Args:
        product: The product dictionary
        
    Returns:
        A generated description
    """
    name = product.get("name", "")
    brand = extract_brand(product)
    
    # Extract main category if available
    category_name = ""
    if "categories" in product and product["categories"]:
        for category in product["categories"]:
            if category.get("isMainCategory", False) and "name" in category:
                category_name = category["name"]
                break
        
        # If no main category found, use the first one
        if not category_name and "name" in product["categories"][0]:
            category_name = product["categories"][0]["name"]
    
    # Check if there's a description in properties
    prop_desc = extract_property_value(product, "Description") or \
                extract_property_value(product, "description")
    
    if prop_desc:
        return prop_desc
    
    # Generate a description from available data
    elements = []
    if name:
        elements.append(name)
    
    if category_name:
        elements.append(f"Kategori: {category_name}")
    
    if brand and brand != "Unknown Brand":
        elements.append(f"Leverandør: {brand}")
    
    # Add additional properties that might be useful
    for key in ["Material", "Size", "Weight", "Color", "Farge"]:
        value = extract_property_value(product, key)
        if value:
            elements.append(f"{key}: {value}")
    
    return ". ".join(elements)


def extract_price_info(product: Dict[str, Any]) -> tuple:
    """
    Extract price information from the product.
    
    Args:
        product: The product dictionary
        
    Returns:
        Tuple of (priceOriginal, priceCurrent, isOnSale)
    """
    price_original = 0.0
    price_current = 0.0
    is_on_sale = False
    
    # Check if there are prices
    if "prices" not in product or not product["prices"]:
        return price_original, price_current, is_on_sale
    
    try:
        # Priority: b2c_nor, then b2c_swe, then b2b_nor
        preferred_markets = ["b2c_nor", "b2c_swe", "b2b_nor"]
        
        # Create a lookup by market ID, with safer key access
        prices_by_market = {}
        for p in product["prices"]:
            if isinstance(p, dict) and "marketId" in p and "unitPrice" in p:
                prices_by_market[p["marketId"]] = p
        
        # Find the first available preferred market
        for market in preferred_markets:
            if market in prices_by_market:
                price_data = prices_by_market[market]
                
                # Get current price
                price_current = float(price_data["unitPrice"])
                
                # Get original price if available, otherwise same as current
                if "originalUnitPrice" in price_data and price_data["originalUnitPrice"]:
                    price_original = float(price_data["originalUnitPrice"])
                else:
                    price_original = price_current
                
                # Determine if on sale
                is_on_sale = price_original > price_current
                
                break
        
        # If no preferred market was found, use the first available price
        if price_original == 0.0 and price_current == 0.0 and product["prices"]:
            # Safely access the first price
            for first_price in product["prices"]:
                if isinstance(first_price, dict) and "unitPrice" in first_price:
                    price_current = float(first_price["unitPrice"])
                    
                    if "originalUnitPrice" in first_price and first_price["originalUnitPrice"]:
                        price_original = float(first_price["originalUnitPrice"])
                    else:
                        price_original = price_current
                        
                    is_on_sale = price_original > price_current
                    break
    except Exception as e:
        logger.warning(f"Error extracting price info: {str(e)}. Using default values.")
    
    return price_original, price_current, is_on_sale


def extract_color(product: Dict[str, Any]) -> Optional[str]:
    """
    Extract color information from the product.
    
    Args:
        product: The product dictionary
        
    Returns:
        Color string or None if not found
    """
    # Check common property keys for color
    color_keys = ["Color", "Farge", "colour", "Colour", "color"]
    
    for key in color_keys:
        color = extract_property_value(product, key)
        if color:
            return color
    
    # Try to extract color from the name
    if "name" in product and product["name"]:
        # Common color names (expand as needed)
        colors = ["red", "blue", "green", "yellow", "black", "white", "grey", "gray", 
                 "purple", "orange", "brown", "pink", "silver", "gold", "beige"]
        
        name_lower = product["name"].lower()
        for color in colors:
            if color in name_lower:
                return color.capitalize()
    
    return None


def extract_age_range(product: Dict[str, Any]) -> tuple:
    """
    Extract age range information from the product.
    
    Args:
        product: The product dictionary
        
    Returns:
        Tuple of (ageFrom, ageTo, ageBucket)
    """
    age_from = None
    age_to = None
    age_bucket = None
    
    # Check for explicit age fields in properties
    age_from_value = extract_property_value(product, "AgeFrom") or \
                    extract_property_value(product, "MinAge") or \
                    extract_property_value(product, "ageFrom")
                    
    age_to_value = extract_property_value(product, "AgeTo") or \
                extract_property_value(product, "MaxAge") or \
                extract_property_value(product, "ageTo")
    
    # Try to convert to integers
    if age_from_value:
        try:
            age_from = int(float(age_from_value))
        except (ValueError, TypeError):
            pass
    
    if age_to_value:
        try:
            age_to = int(float(age_to_value))
        except (ValueError, TypeError):
            pass
    
    # Check for age bucket in properties
    age_bucket = extract_property_value(product, "AgeBucket") or \
                extract_property_value(product, "AgeGroup") or \
                extract_property_value(product, "ageBucket")
    
    # If we have ages but no bucket, generate one
    if age_from is not None and age_to is not None and not age_bucket:
        age_bucket = f"{age_from} to {age_to} years"
    
    # Try to extract from the name if still missing
    if age_from is None and age_to is None and not age_bucket:
        if "name" in product and product["name"]:
            # Look for patterns like "0-6 months", "1-3 years", etc.
            age_patterns = [
                r'(\d+)-(\d+)\s+month',  # e.g., "0-6 months"
                r'(\d+)-(\d+)\s+år',     # e.g., "1-3 år" (Norwegian)
                r'(\d+)-(\d+)\s+year',   # e.g., "1-3 years"
            ]
            
            for pattern in age_patterns:
                match = re.search(pattern, product["name"], re.IGNORECASE)
                if match:
                    try:
                        age_from = int(match.group(1))
                        age_to = int(match.group(2))
                        
                        # Create age bucket based on match
                        if "month" in match.group(0).lower():
                            age_bucket = f"{age_from} to {age_to} months"
                        else:
                            age_bucket = f"{age_from} to {age_to} years"
                        
                        break
                    except (ValueError, IndexError):
                        pass
    
    return age_from, age_to, age_bucket


def extract_stock_level(product: Dict[str, Any]) -> int:
    """
    Extract stock level information from the product.
    
    Args:
        product: The product dictionary
        
    Returns:
        Stock level as integer
    """
    # Check for inventory fields
    if "availableInventory" in product:
        try:
            return int(float(product["availableInventory"]))
        except (ValueError, TypeError):
            pass
    
    # Check in properties
    stock = extract_property_value(product, "StockLevel") or \
           extract_property_value(product, "Stock") or \
           extract_property_value(product, "Inventory")
    
    if stock:
        try:
            return int(float(stock))
        except (ValueError, TypeError):
            pass
    
    # Default to 0 if no stock information
    return 0


def extract_seasons(product: Dict[str, Any]) -> Optional[List[str]]:
    """
    Extract season information from the product.
    
    Args:
        product: The product dictionary
        
    Returns:
        List of seasons or None if not found
    """
    # Check for seasons in properties
    seasons_value = extract_property_value(product, "Seasons") or \
                  extract_property_value(product, "Season")
    
    if seasons_value:
        # If it's a comma or semicolon separated string, split it
        if isinstance(seasons_value, str):
            if "," in seasons_value:
                return [s.strip() for s in seasons_value.split(",")]
            elif ";" in seasons_value:
                return [s.strip() for s in seasons_value.split(";")]
            else:
                return [seasons_value.strip()]
        
        # If it's already a list, return it
        elif isinstance(seasons_value, list):
            return seasons_value
    
    # Try to infer from product name or categories
    seasonal_terms = {
        "winter": ["winter", "vinter", "snow", "snø", "christmas", "jul"],
        "spring": ["spring", "vår", "easter", "påske"],
        "summer": ["summer", "sommer", "beach", "strand", "pool", "swimming", "swimwear"],
        "fall": ["fall", "autumn", "høst", "halloween"]
    }
    
    found_seasons = set()
    
    # Check in name
    if "name" in product and product["name"]:
        name_lower = product["name"].lower()
        
        for season, terms in seasonal_terms.items():
            if any(term in name_lower for term in terms):
                found_seasons.add(season)
    
    # Check in categories
    if "categories" in product and product["categories"]:
        for category in product["categories"]:
            if "name" in category and category["name"]:
                cat_lower = category["name"].lower()
                
                for season, terms in seasonal_terms.items():
                    if any(term in cat_lower for term in terms):
                        found_seasons.add(season)
    
    if found_seasons:
        return list(found_seasons)
    
    return None


def transform_product(product: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform a product from Omnium format to MongoDB Atlas format.
    
    Args:
        product: The product dictionary in Omnium format
        
    Returns:
        Transformed product dictionary
    """
    try:
        # Extract required fields
        product_id = f"{product['id']}_no"  # Append market identifier
        product_name = product.get("name", "")
        if not product_name:
            product_name = "Unnamed Product"
        
        # Extract additional fields with safe handling
        try:
            brand = extract_brand(product)
        except Exception as e:
            logger.warning(f"Error extracting brand: {str(e)}. Using default value.")
            brand = "Unknown Brand"
            
        try:
            description = extract_description(product)
        except Exception as e:
            logger.warning(f"Error extracting description: {str(e)}. Using product name.")
            description = product_name
            
        try:
            price_original, price_current, is_on_sale = extract_price_info(product)
        except Exception as e:
            logger.warning(f"Error extracting price: {str(e)}. Using default values.")
            price_original, price_current, is_on_sale = 0.0, 0.0, False
            
        try:
            age_from, age_to, age_bucket = extract_age_range(product)
        except Exception as e:
            logger.warning(f"Error extracting age range: {str(e)}. Using default values.")
            age_from, age_to, age_bucket = None, None, None
            
        try:
            color = extract_color(product)
        except Exception as e:
            logger.warning(f"Error extracting color: {str(e)}. Using default value.")
            color = None
            
        try:
            stock_level = extract_stock_level(product)
        except Exception as e:
            logger.warning(f"Error extracting stock level: {str(e)}. Using default value.")
            stock_level = 0
            
        try:
            seasons = extract_seasons(product)
        except Exception as e:
            logger.warning(f"Error extracting seasons: {str(e)}. Using default value.")
            seasons = None
        
        # Create transformed product
        transformed = {
            "id": product_id,
            "title": product_name,
            "description": description,
            "brand": brand,
            "imageThumbnailUrl": "",  # Default empty string
            "priceOriginal": price_original,
            "priceCurrent": price_current,
            "isOnSale": is_on_sale,
            "ageFrom": age_from,
            "ageTo": age_to,
            "ageBucket": age_bucket,
            "color": color,
            "seasons": seasons,
            "productType": DEFAULT_PRODUCT_TYPE,
            "seasonRelevancyFactor": DEFAULT_SEASON_RELEVANCY,
            "stockLevel": stock_level
        }
        
        return transformed
    except Exception as e:
        logger.error(f"Failed to transform product: {str(e)}")
        raise


def transform_data(input_file: str, output_file: str, limit: Optional[int] = None, batch_size: int = 500) -> None:
    """
    Transform product data from Omnium format to MongoDB Atlas format.
    
    Args:
        input_file: Path to the input JSON file
        output_file: Path to the output JSON file
        limit: Maximum number of products to process (optional)
        batch_size: Number of products to process in each batch (default: 500)
    """
    logger.info(f"Starting data transformation from {input_file} to {output_file}")
    
    try:
        # Read the input file
        logger.info("Reading input file...")
        with open(input_file, "r", encoding="utf-8") as f:
            source_data = json.load(f)
        
        # Check if the file has the expected structure
        if "result" not in source_data:
            raise ValueError("Input file does not contain 'result' field")
        
        # Get the product list
        source_products = source_data["result"]
        total_products = len(source_products)
        logger.info(f"Found {total_products} products in source data")
        
        # Apply limit if specified
        if limit and limit < total_products:
            logger.info(f"Limiting to {limit} products")
            source_products = source_products[:limit]
            total_products = limit
        
        # Process in batches to manage memory usage
        transformed_products = []
        processed_ids = set()  # Track IDs to avoid duplicates
        total_batches = (total_products + batch_size - 1) // batch_size  # Ceiling division
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min((batch_num + 1) * batch_size, total_products)
            batch = source_products[start_idx:end_idx]
            
            logger.info(f"Processing batch {batch_num + 1}/{total_batches} (products {start_idx + 1}-{end_idx})")
            
            # Transform products in this batch
            batch_transformed = []
            
            for i, product in enumerate(batch, 1):
                product_idx = start_idx + i
                if i % 100 == 0 or i == len(batch):
                    logger.info(f"Transforming product {product_idx}/{total_products}")
                
                try:
                    # Skip products without ID
                    if "id" not in product or not product["id"]:
                        logger.warning(f"Skipping product at index {product_idx-1}: No ID")
                        continue
                    
                    # Skip duplicate IDs
                    if product["id"] in processed_ids:
                        logger.warning(f"Skipping duplicate product ID: {product['id']}")
                        continue
                    
                    transformed = transform_product(product)
                    batch_transformed.append(transformed)
                    processed_ids.add(product["id"])
                    
                except Exception as e:
                    logger.error(f"Error transforming product at index {product_idx-1}: {str(e)}")
                    continue
            
            # Add batch results to the total
            transformed_products.extend(batch_transformed)
            
            # Force garbage collection to free memory after each batch
            import gc
            gc.collect()
        
        # Write output file
        logger.info(f"Writing {len(transformed_products)} transformed products to {output_file}")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(transformed_products, f, indent=2, ensure_ascii=False)
        
        logger.info("Transformation complete")
        logger.info(f"Total products in source: {total_products}")
        logger.info(f"Total products transformed: {len(transformed_products)}")
        
    except Exception as e:
        logger.error(f"Error during transformation: {str(e)}")
        raise


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Transform product data from Omnium format to MongoDB Atlas format")
    parser.add_argument("--input", required=True, help="Path to the input JSON file")
    parser.add_argument("--output", required=True, help="Path to the output JSON file")
    parser.add_argument("--limit", type=int, help="Maximum number of products to process")
    parser.add_argument("--batch-size", type=int, default=500, help="Number of products to process in each batch (default: 500)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    transform_data(args.input, args.output, args.limit, args.batch_size)
