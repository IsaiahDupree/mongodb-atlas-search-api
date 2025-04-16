#!/usr/bin/env python
"""
Product Data Validation Script

This script validates transformed product data against the schema required
by the MongoDB Atlas Search API.

Usage:
    python validate_data.py --input <input_file> [--report <report_file>]

Arguments:
    --input     Path to the transformed JSON file to validate
    --report    Path to the validation report output file (optional)
"""

import argparse
import json
import logging
import sys
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("data_validate")

# Product schema requirements
REQUIRED_FIELDS = {
    "id": str,
    "title": str,
    "description": str,
    "brand": str,
    "priceOriginal": (int, float),
    "priceCurrent": (int, float),
    "isOnSale": bool,
    "productType": str,
    "seasonRelevancyFactor": (int, float),
    "stockLevel": int
}

OPTIONAL_FIELDS = {
    "imageThumbnailUrl": str,
    "ageFrom": (int, type(None)),
    "ageTo": (int, type(None)),
    "ageBucket": (str, type(None)),
    "color": (str, type(None)),
    "seasons": (list, type(None))
}

# Validation constraints
CONSTRAINTS = {
    "title": {"min_length": 2, "max_length": 200},
    "description": {"min_length": 5, "max_length": 2000},
    "brand": {"min_length": 1, "max_length": 100},
    "priceOriginal": {"min": 0},
    "priceCurrent": {"min": 0},
    "seasonRelevancyFactor": {"min": 0, "max": 1},
    "stockLevel": {"min": 0},
    "id": {"regex": r"^[a-zA-Z0-9_-]+"}
}


def validate_field_type(field_name: str, value: Any, expected_type: Any) -> Tuple[bool, str]:
    """
    Validate that a field has the expected type.
    
    Args:
        field_name: Name of the field
        value: Value to validate
        expected_type: Expected type or tuple of types
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if isinstance(expected_type, tuple):
        if not isinstance(value, expected_type):
            type_names = " or ".join(str(t.__name__) for t in expected_type)
            return False, f"Field '{field_name}' has type {type(value).__name__}, expected {type_names}"
    else:
        if not isinstance(value, expected_type):
            return False, f"Field '{field_name}' has type {type(value).__name__}, expected {expected_type.__name__}"
    
    return True, ""


def validate_constraints(field_name: str, value: Any) -> Tuple[bool, str]:
    """
    Validate that a field meets additional constraints.
    
    Args:
        field_name: Name of the field
        value: Value to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if field_name not in CONSTRAINTS:
        return True, ""
    
    constraints = CONSTRAINTS[field_name]
    
    # Check string length constraints
    if isinstance(value, str):
        if "min_length" in constraints and len(value) < constraints["min_length"]:
            return False, f"Field '{field_name}' is too short ({len(value)} chars, min {constraints['min_length']})"
        
        if "max_length" in constraints and len(value) > constraints["max_length"]:
            return False, f"Field '{field_name}' is too long ({len(value)} chars, max {constraints['max_length']})"
        
        if "regex" in constraints and not re.match(constraints["regex"], value):
            return False, f"Field '{field_name}' does not match required pattern"
    
    # Check numeric constraints
    if isinstance(value, (int, float)):
        if "min" in constraints and value < constraints["min"]:
            return False, f"Field '{field_name}' is too small ({value}, min {constraints['min']})"
        
        if "max" in constraints and value > constraints["max"]:
            return False, f"Field '{field_name}' is too large ({value}, max {constraints['max']})"
    
    # Check list constraints
    if isinstance(value, list):
        if "min_items" in constraints and len(value) < constraints["min_items"]:
            return False, f"Field '{field_name}' has too few items ({len(value)}, min {constraints['min_items']})"
        
        if "max_items" in constraints and len(value) > constraints["max_items"]:
            return False, f"Field '{field_name}' has too many items ({len(value)}, max {constraints['max_items']})"
    
    return True, ""


def validate_product(product: Dict[str, Any], index: int) -> List[str]:
    """
    Validate a single product against the schema.
    
    Args:
        product: Product dictionary to validate
        index: Index of the product in the dataset (for error reporting)
        
    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    
    # Check required fields
    for field_name, expected_type in REQUIRED_FIELDS.items():
        if field_name not in product:
            errors.append(f"Required field '{field_name}' is missing")
            continue
        
        # Validate type
        is_valid, error = validate_field_type(field_name, product[field_name], expected_type)
        if not is_valid:
            errors.append(error)
        
        # Validate constraints
        is_valid, error = validate_constraints(field_name, product[field_name])
        if not is_valid:
            errors.append(error)
    
    # Check optional fields
    for field_name, expected_type in OPTIONAL_FIELDS.items():
        if field_name in product and product[field_name] is not None:
            # Validate type
            is_valid, error = validate_field_type(field_name, product[field_name], expected_type)
            if not is_valid:
                errors.append(error)
            
            # Validate constraints
            is_valid, error = validate_constraints(field_name, product[field_name])
            if not is_valid:
                errors.append(error)
    
    # Check for unexpected fields
    for field_name in product:
        if field_name not in REQUIRED_FIELDS and field_name not in OPTIONAL_FIELDS:
            errors.append(f"Unexpected field '{field_name}'")
    
    # Semantic validation
    if "priceOriginal" in product and "priceCurrent" in product and "isOnSale" in product:
        price_original = product["priceOriginal"]
        price_current = product["priceCurrent"]
        is_on_sale = product["isOnSale"]
        
        # Check if isOnSale is consistent with prices
        if price_original > price_current and not is_on_sale:
            errors.append(f"isOnSale is False but priceOriginal ({price_original}) > priceCurrent ({price_current})")
        elif price_original <= price_current and is_on_sale:
            errors.append(f"isOnSale is True but priceOriginal ({price_original}) <= priceCurrent ({price_current})")
    
    # Check age range consistency
    if "ageFrom" in product and "ageTo" in product:
        age_from = product["ageFrom"]
        age_to = product["ageTo"]
        
        if age_from is not None and age_to is not None and age_from > age_to:
            errors.append(f"ageFrom ({age_from}) is greater than ageTo ({age_to})")
    
    return errors


def validate_data(input_file: str, report_file: Optional[str] = None) -> Dict[str, Any]:
    """
    Validate product data against the schema.
    
    Args:
        input_file: Path to the input JSON file
        report_file: Path to the validation report output file (optional)
        
    Returns:
        Validation report dictionary
    """
    logger.info(f"Starting data validation for {input_file}")
    
    try:
        # Read input file
        logger.info("Reading input file...")
        with open(input_file, "r", encoding="utf-8") as f:
            products = json.load(f)
        
        total_products = len(products)
        logger.info(f"Found {total_products} products to validate")
        
        # Validate products
        validation_results = {
            "total_products": total_products,
            "valid_products": 0,
            "invalid_products": 0,
            "field_coverage": {},
            "errors": [],
            "unique_errors": {}
        }
        
        # Initialize field coverage
        for field in list(REQUIRED_FIELDS.keys()) + list(OPTIONAL_FIELDS.keys()):
            validation_results["field_coverage"][field] = 0
        
        # Track duplicate IDs
        product_ids = set()
        duplicate_ids = set()
        
        # Validate each product
        for i, product in enumerate(products):
            if i % 100 == 0 or i == total_products - 1:
                logger.info(f"Validating product {i+1}/{total_products}")
            
            # Check for duplicate IDs
            if "id" in product and product["id"]:
                if product["id"] in product_ids:
                    duplicate_ids.add(product["id"])
                else:
                    product_ids.add(product["id"])
            
            # Track field coverage
            for field in validation_results["field_coverage"]:
                if field in product and product[field] is not None:
                    validation_results["field_coverage"][field] += 1
            
            # Validate the product
            errors = validate_product(product, i)
            
            if errors:
                validation_results["invalid_products"] += 1
                validation_results["errors"].append({
                    "index": i,
                    "id": product.get("id", "unknown"),
                    "errors": errors
                })
                
                # Track unique error types
                for error in errors:
                    error_type = error.split(":")[0] if ":" in error else error
                    if error_type not in validation_results["unique_errors"]:
                        validation_results["unique_errors"][error_type] = 0
                    validation_results["unique_errors"][error_type] += 1
            else:
                validation_results["valid_products"] += 1
        
        # Convert field coverage to percentages
        for field in validation_results["field_coverage"]:
            count = validation_results["field_coverage"][field]
            validation_results["field_coverage"][field] = {
                "count": count,
                "percentage": round(count / total_products * 100, 2) if total_products > 0 else 0
            }
        
        # Add duplicate ID information
        validation_results["duplicate_ids"] = {
            "count": len(duplicate_ids),
            "ids": list(duplicate_ids) if len(duplicate_ids) <= 10 else list(duplicate_ids)[:10] + ["..."]
        }
        
        # Write report if requested
        if report_file:
            logger.info(f"Writing validation report to {report_file}")
            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(validation_results, f, indent=2, ensure_ascii=False)
        
        # Log summary
        logger.info("Validation complete")
        logger.info(f"Total products: {total_products}")
        logger.info(f"Valid products: {validation_results['valid_products']}")
        logger.info(f"Invalid products: {validation_results['invalid_products']}")
        
        if validation_results["invalid_products"] > 0:
            logger.info("Top error types:")
            for error_type, count in sorted(validation_results["unique_errors"].items(), 
                                           key=lambda x: x[1], reverse=True)[:5]:
                logger.info(f"  - {error_type}: {count} occurrences")
        
        if validation_results["duplicate_ids"]["count"] > 0:
            logger.info(f"Found {validation_results['duplicate_ids']['count']} duplicate product IDs")
        
        return validation_results
        
    except Exception as e:
        logger.error(f"Error during validation: {str(e)}")
        raise


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Validate transformed product data")
    parser.add_argument("--input", required=True, help="Path to the input JSON file")
    parser.add_argument("--report", help="Path to the validation report output file")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    validate_data(args.input, args.report)
