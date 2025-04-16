# Data Transformation

This document outlines the process of transforming the source product data into the format expected by the MongoDB Atlas Search API.

## Transformation Requirements

Our transformation script must:

1. Read the source JSON file
2. Map fields from source to target schema
3. Handle missing or inconsistent data
4. Generate derived fields when needed
5. Output a properly formatted JSON file ready for ingestion

## Transformation Script Overview

The transformation script (`transform_data.py`) performs the following steps:

1. Parse the source JSON file
2. Iterate through each product in the `result` array
3. Extract and transform fields according to the mapping strategy
4. Validate the transformed data against the target schema
5. Write the transformed products to an output file

## Usage

```bash
python scripts/transform_data.py \
  --input "Omnium_Search_Products_START-1742999880951/Omnium_Search_Products_START-1742999880951.json" \
  --output "transformed_products.json" \
  --limit 100  # Optional: process only a subset of products
```

## Key Transformation Functions

The script includes several helper functions to extract and transform specific fields:

- `extract_description(product)`: Generate a description from available data
- `extract_brand(product)`: Find the brand from properties
- `extract_price_info(product)`: Extract price information for the appropriate market
- `extract_age_range(product)`: Parse age-related information
- `extract_color(product)`: Find color information
- `derive_product_type(product)`: Determine the product type
- `extract_property_value(product, key, group=None)`: Generic function to extract values from the properties array

## Special Handling Logic

### Category Handling

Categories in the source data are hierarchical, but our target model doesn't have a direct category field. We'll extract the main category name and include it in the description for better searchability.

### Price Selection

The source data contains prices for multiple markets (B2B and B2C). We'll prioritize the B2C Norwegian (b2c_nor) price as the primary consumer-facing price.

### Description Generation

Many products lack a formal description. We'll generate a description by combining:
- Product name
- Main category
- Key properties (material, size, color, etc.)
- Any available marketing text

### Missing Required Fields

For missing required fields, we'll use intelligent defaults:
- Missing `brand`: "Unknown Brand"
- Missing `description`: Generated from product name and categories
- Missing `price`: 0.0 with a flag indicating price unavailable

## Data Cleaning

The transformation script also performs data cleaning:
- Remove HTML tags from text fields
- Normalize price values to ensure they're numeric
- Standardize language codes
- Trim whitespace from string values

## Output Format

The output is a JSON array of products, each conforming to the target model schema:

```json
[
  {
    "id": "4893156034908_no",
    "title": "Aktivitetspakke, Creepy Crawley Digging",
    "description": "Aktivitetspakke for barn. Kategori: Ukategoriserte (INNKJØP). Leverandør: Døvigen.",
    "brand": "Døvigen",
    "imageThumbnailUrl": "",
    "priceOriginal": 349.0,
    "priceCurrent": 349.0,
    "isOnSale": false,
    "ageFrom": null,
    "ageTo": null,
    "ageBucket": null,
    "color": null,
    "seasons": null,
    "productType": "main",
    "seasonRelevancyFactor": 0.5,
    "stockLevel": 0
  },
  // Additional transformed products...
]
```

## Validation

After transformation, the script performs basic validation to ensure all products have the required fields and appropriate data types. Any validation issues are logged for review.
