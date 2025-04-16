# MongoDB Atlas Search Technical Implementation Guide

## Overview

This technical guide provides detailed implementation information for processing Omnium product data with the MongoDB Atlas Search API. It complements the higher-level project documentation by focusing on the technical details of the implementation.

## Environment Setup

### Prerequisites

- Python 3.8+
- MongoDB Atlas cluster with Search enabled
- Docker and Docker Compose (for running the API locally)
- API key for authentication

### Directory Structure

```
├── app/                       # MongoDB Atlas Search API
│   ├── models/                # Data models for the API
│   │   └── product.py         # Product data model
│   └── ...
├── docs/                      # Project documentation
│   ├── data_processing/       # Data processing documentation
│   ├── Omnium_Data_Integration_Project.md  # Project overview
│   └── Technical_Implementation_Guide.md   # This guide
├── scripts/                   # Processing scripts
│   └── data_processing/       # Data processing scripts
│       ├── transform_data.py  # Data transformation script
│       ├── validate_data.py   # Data validation script
│       ├── ingest_data.py     # Data ingestion script
│       └── test_search.py     # Search testing script
└── Omnium_Search_Products_START-1742999880951/  # Source data
    └── Omnium_Search_Products_START-1742999880951.json
```

## Technical Implementation

### 1. Data Transformation (transform_data.py)

#### Key Functions

- `transform_data(input_file, output_file, limit)`: Main function that orchestrates the transformation process
- `transform_product(product)`: Transforms a single product
- `extract_property_value(product, key, group)`: Extracts a value from the properties array
- `extract_brand(product)`: Identifies the brand from various sources
- `extract_description(product)`: Generates a description from available data
- `extract_price_info(product)`: Extracts and prioritizes price information
- `extract_color(product)`: Identifies color information
- `extract_age_range(product)`: Parses age-related information
- `extract_stock_level(product)`: Determines stock level
- `extract_seasons(product)`: Identifies seasonal products

#### Implementation Details

The transformation process handles several challenges:

1. **Property Extraction**:
   ```python
   def extract_property_value(product, key, group=None):
       if "properties" not in product:
           return None
           
       for prop in product["properties"]:
           if prop["key"] == key:
               if group is None or ("keyGroup" in prop and prop["keyGroup"] == group):
                   return prop["value"]
       return None
   ```

2. **Price Selection Logic**:
   ```python
   # Priority: b2c_nor, then b2c_swe, then b2b_nor
   preferred_markets = ["b2c_nor", "b2c_swe", "b2b_nor"]
   
   # Create a lookup by market ID
   prices_by_market = {p["marketId"]: p for p in product["prices"] 
                      if "marketId" in p and "unitPrice" in p}
   
   # Find the first available preferred market
   for market in preferred_markets:
       if market in prices_by_market:
           price_data = prices_by_market[market]
           # Extract price information
   ```

3. **Description Generation**:
   ```python
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
   ```

### 2. Data Validation (validate_data.py)

#### Schema Definition

The validation script defines the expected schema:

```python
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
```

#### Validation Constraints

Additional constraints are defined for field values:

```python
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
```

#### Validation Logic

The validation process includes several checks:

1. **Type Checking**: Ensures fields have the expected data types
2. **Constraint Validation**: Verifies fields meet length, range, and pattern requirements
3. **Semantic Validation**: Checks for logical consistency (e.g., isOnSale is consistent with prices)
4. **Field Coverage Analysis**: Tracks the percentage of products with each field populated
5. **Duplicate ID Detection**: Identifies products with duplicate IDs

### 3. Data Ingestion (ingest_data.py)

#### API Interaction

The ingestion script interacts with the API using the `requests` library:

```python
def ingest_batch(api_url, api_key, batch, session):
    ingest_url = f"{api_url.rstrip('/')}/ingest/products"
    
    headers = {
        "Content-Type": "application/json",
        "x-apikey": api_key
    }
    
    response = session.post(
        ingest_url,
        headers=headers,
        json=batch,
        timeout=DEFAULT_TIMEOUT
    )
    
    response.raise_for_status()
    return response.json()
```

#### Batch Processing

To handle large datasets, the script processes products in batches:

```python
# Split into batches
batches = [products[i:i + batch_size] for i in range(0, len(products), batch_size)]
logger.info(f"Split into {len(batches)} batches of up to {batch_size} products each")

# Ingest batches
for i, batch in enumerate(batches, 1):
    batch_start_time = time.time()
    logger.info(f"Ingesting batch {i}/{len(batches)} ({len(batch)} products)")
    
    try:
        result = ingest_batch(api_url, api_key, batch, session)
        # Process result...
```

#### Error Handling

The script implements robust error handling with retries:

```python
# Configure retry strategy
retry_strategy = Retry(
    total=MAX_RETRIES,
    backoff_factor=RETRY_BACKOFF,
    status_forcelist=[408, 429, 500, 502, 503, 504],
    allowed_methods=["GET", "POST"]
)

adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)
```

### 4. Search Testing (test_search.py)

#### Test Queries

The script includes a variety of test queries to evaluate different search scenarios:

```python
TEST_QUERIES = [
    {
        "name": "Basic keyword search",
        "query": {
            "query": "aktivitetspakke",
            "limit": 10
        }
    },
    {
        "name": "Filtered search by price range",
        "query": {
            "query": "lego",
            "filters": {
                "priceRange": {
                    "min": 100,
                    "max": 500
                }
            },
            "limit": 10
        }
    },
    # Additional test queries...
]
```

#### Results Analysis

For each query, the script analyzes the search results:

```python
analysis = {
    "query_name": query_name,
    "query": query,
    "total_results": results.get("total", 0),
    "results_count": len(results.get("products", [])),
    "response_time_ms": response_time,
    "top_products": [],
    "has_facets": "facets" in results and results["facets"] is not None,
    "facet_count": len(results.get("facets", [])) if "facets" in results else 0,
    "query_explanation": "query_explanation" in results
}

# Add top 3 products
for i, product in enumerate(results.get("products", [])[:3]):
    analysis["top_products"].append({
        "position": i + 1,
        "id": product.get("id", "unknown"),
        "title": product.get("title", "unknown"),
        "brand": product.get("brand", "unknown"),
        "price": product.get("priceCurrent", 0)
    })
```

## Usage Examples

### 1. Transforming a Subset of Products

```bash
python scripts\data_processing\transform_data.py --input "Omnium_Search_Products_START-1742999880951\Omnium_Search_Products_START-1742999880951.json" --output "transformed_subset.json" --limit 1000
```

### 2. Validating Transformed Data

```bash
python scripts\data_processing\validate_data.py --input "transformed_subset.json" --report "validation_report.json"
```

### 3. Ingesting Data with a Custom Batch Size

```bash
python scripts\data_processing\ingest_data.py --input "transformed_subset.json" --api-url "http://localhost:8000" --api-key "your_default_api_key" --batch-size 50
```

### 4. Running Search Tests with Output

```bash
python scripts\data_processing\test_search.py --api-url "http://localhost:8000" --api-key "your_default_api_key" --output "search_results.json"
```

## Performance Optimization

### Memory Management

For large datasets, consider these memory optimization techniques:

1. **Streaming Processing**: Modify the transformation script to process the input file in chunks.
2. **Batch Limits**: Use the `--limit` parameter to process manageable subsets.
3. **Garbage Collection**: Add explicit garbage collection calls for long-running processes.

### API Performance

To optimize API interaction:

1. **Batch Size Tuning**: Adjust batch size based on server capacity and network conditions.
2. **Concurrency**: Consider implementing concurrent batch processing for ingestion.
3. **Request Throttling**: Add delays between requests to avoid overwhelming the API.

## Troubleshooting

### Common Issues

1. **JSON Parsing Errors**:
   - Check for malformed JSON in the source file
   - Use a JSON validator to identify specific issues

2. **Memory Errors**:
   ```
   MemoryError: ...
   ```
   - Reduce the batch size or limit
   - Consider streaming processing

3. **API Connection Errors**:
   ```
   ConnectionError: Max retries exceeded with url: ...
   ```
   - Verify the API is running
   - Check network connectivity
   - Increase timeout values

4. **Validation Failures**:
   ```
   Field 'title' has type NoneType, expected str
   ```
   - Check the source data for missing required fields
   - Add default values for missing fields in the transformation script

### Debugging Tips

1. **Logging**: Increase logging verbosity for detailed information:
   ```python
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Sample Inspection**: Examine problematic records:
   ```python
   print(json.dumps(product, indent=2))
   ```

3. **API Response Inspection**:
   ```python
   print(response.status_code, response.text)
   ```

## MongoDB Atlas Configuration

For optimal vector search performance, configure your MongoDB Atlas cluster with:

```json
{
  "mappings": {
    "dynamic": true,
    "fields": {
      "title_embedding": {
        "type": "knnVector",
        "dimensions": 384,
        "similarity": "cosine"
      },
      "description_embedding": {
        "type": "knnVector",
        "dimensions": 384,
        "similarity": "cosine"
      }
    }
  }
}
```

## Security Considerations

1. **API Key Management**: Never hardcode API keys in scripts. Use environment variables or a secure key storage solution.

2. **Network Security**: Consider using HTTPS for all API communication.

3. **Input Validation**: Validate all user inputs before processing them.

4. **Error Handling**: Be careful not to expose sensitive information in error messages.

## Conclusion

This technical guide provides detailed implementation information for processing Omnium product data with the MongoDB Atlas Search API. By following these guidelines and examples, you should be able to successfully transform, validate, ingest, and search product data.
