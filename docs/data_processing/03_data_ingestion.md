# Data Ingestion

This document outlines the process of ingesting the transformed product data into the MongoDB Atlas Search API.

## Prerequisites

Before ingestion, ensure:

1. The MongoDB Atlas Search API is running
2. You have the correct API key for authentication
3. The product data has been transformed to the correct format
4. MongoDB Atlas vector search indexes are configured properly

## Ingestion Script Overview

The ingestion script (`ingest_data.py`) performs the following steps:

1. Read the transformed product data file
2. Split the data into manageable batches
3. Send each batch to the API's ingestion endpoint
4. Track progress and handle any errors
5. Verify successful ingestion

## Usage

```bash
python scripts/ingest_data.py \
  --input "transformed_products.json" \
  --api-url "http://localhost:8000" \
  --api-key "your_api_key" \
  --batch-size 100
```

## API Endpoints Used

The script uses the following API endpoints:

- `POST /ingest/products` - To ingest product data
- `GET /health` - To verify API availability
- `GET /doc/{product_id}` - To verify ingestion of specific products

## Batching Strategy

To avoid overwhelming the API, products are ingested in batches. The default batch size is 100 products per request, but this can be adjusted based on your system's performance.

## Error Handling

The script implements the following error handling strategies:

1. **Connection errors**: Retry with exponential backoff
2. **API errors**: Log error details and continue with next batch
3. **Validation errors**: Log problematic products and continue

## Progress Tracking

During ingestion, the script provides real-time progress updates:

```
Ingesting products: Batch 1/50 (100 products)
Batch 1 successful: 98 inserted, 2 updated
Ingesting products: Batch 2/50 (100 products)
Batch 2 successful: 100 inserted, 0 updated
...
```

## Verification

After ingestion, the script performs verification by:

1. Sampling random products from the ingested data
2. Querying the API to verify they exist
3. Checking that fields were ingested correctly
4. Reporting any discrepancies

## Post-Ingestion Tasks

After successful ingestion, consider performing these tasks:

1. **Index verification**: Ensure all vector indexes are built and optimized
2. **Search testing**: Perform sample searches to verify functionality
3. **Performance measurement**: Record baseline query performance
4. **Cleanup**: Remove any temporary files from the transformation process

## Common Issues and Solutions

### Slow Ingestion Performance

If ingestion is slow, try:
- Reducing batch size
- Running the script on a machine closer to the API server
- Ensuring the MongoDB server has adequate resources

### Missing Embeddings

If products are ingested but lack vector embeddings:
- Verify the embedding service is running
- Check that title and description fields contain meaningful text
- Reingest problematic products individually

### API Rate Limiting

If you encounter rate limiting:
- Reduce the ingestion rate by adding delays between batches
- Increase the batch size to reduce the number of API calls
- Verify your API key has appropriate permissions
