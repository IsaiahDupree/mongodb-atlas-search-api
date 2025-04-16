# MongoDB Atlas Search Data Processing Scripts

This directory contains scripts for transforming, validating, ingesting, and testing product data with the MongoDB Atlas Search API.

## Prerequisites

- Python 3.8+
- Required Python packages:
  - requests
  - urllib3

Install dependencies:
```bash
pip install requests urllib3
```

## Script Overview

### 1. Data Transformation

`transform_data.py` - Transforms product data from the Omnium format to the MongoDB Atlas Search API format.

Usage:
```bash
python transform_data.py --input "path/to/input.json" --output "path/to/output.json" [--limit 100]
```

Arguments:
- `--input`: Path to the source JSON file (Omnium format)
- `--output`: Path to the output JSON file (MongoDB format)
- `--limit`: (Optional) Maximum number of products to process

### 2. Data Validation

`validate_data.py` - Validates transformed data against the schema required by the MongoDB Atlas Search API.

Usage:
```bash
python validate_data.py --input "path/to/transformed.json" [--report "path/to/report.json"]
```

Arguments:
- `--input`: Path to the transformed JSON file to validate
- `--report`: (Optional) Path to the validation report output file

### 3. Data Ingestion

`ingest_data.py` - Ingests transformed product data into the MongoDB Atlas Search API.

Usage:
```bash
python ingest_data.py --input "path/to/transformed.json" --api-url "http://localhost:8000" --api-key "your_api_key" [--batch-size 100]
```

Arguments:
- `--input`: Path to the transformed JSON file
- `--api-url`: Base URL of the MongoDB Atlas Search API
- `--api-key`: API key for authentication
- `--batch-size`: (Optional) Number of products to ingest per batch (default: 100)

### 4. Search Testing

`test_search.py` - Tests the search functionality of the MongoDB Atlas Search API.

Usage:
```bash
python test_search.py --api-url "http://localhost:8000" --api-key "your_api_key" [--output "path/to/results.json"]
```

Arguments:
- `--api-url`: Base URL of the MongoDB Atlas Search API
- `--api-key`: API key for authentication
- `--output`: (Optional) Path to output file for search results

## Typical Workflow

1. **Transform** the source data to the required format:
   ```bash
   python transform_data.py --input "../Omnium_Search_Products_START-1742999880951/Omnium_Search_Products_START-1742999880951.json" --output "transformed_products.json" --limit 1000
   ```

2. **Validate** the transformed data:
   ```bash
   python validate_data.py --input "transformed_products.json" --report "validation_report.json"
   ```

3. **Ingest** the validated data into MongoDB Atlas:
   ```bash
   python ingest_data.py --input "transformed_products.json" --api-url "http://localhost:8000" --api-key "your_default_api_key" --batch-size 100
   ```

4. **Test** the search functionality:
   ```bash
   python test_search.py --api-url "http://localhost:8000" --api-key "your_default_api_key" --output "search_results.json"
   ```

## Error Handling

All scripts include comprehensive error handling and logging. If you encounter issues:

1. Check the console output for error messages
2. Verify that the MongoDB Atlas Search API is running
3. Ensure your API key is valid
4. For transformation errors, check that the source data is in the expected format
5. For validation errors, review the validation report
6. For ingestion errors, check the API server logs

## Customization

- The transformation script can be customized to handle different source data formats
- Test queries in `test_search.py` can be modified to test specific search scenarios
- Batch size for ingestion can be adjusted based on your system's performance
