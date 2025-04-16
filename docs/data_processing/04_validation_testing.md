# Validation & Testing

This document outlines the process for validating the transformed data and testing the search functionality after ingestion.

## Data Validation

### Pre-Ingestion Validation

Before ingesting data into MongoDB Atlas, it's important to validate the transformed data:

```bash
python scripts/validate_data.py \
  --input "transformed_products.json" \
  --schema "app/models/product.py" \
  --report "validation_report.json"
```

The validation script checks for:

1. **Schema compliance**: All required fields are present with correct data types
2. **Data quality**: Values are within expected ranges and formats
3. **Consistency**: Related fields have consistent values (e.g., prices, age ranges)
4. **Duplicates**: No duplicate product IDs exist

### Validation Report

The validation script generates a report with:

- Total products validated
- Number of valid/invalid products
- Detailed errors for each invalid product
- Statistics on field coverage (% of products with each field populated)

## Search Testing

After data ingestion, test the search functionality to ensure it meets requirements:

```bash
python scripts/test_search.py \
  --api-url "http://localhost:8000" \
  --api-key "your_api_key" \
  --test-queries "test_queries.json" \
  --report "search_test_report.json"
```

### Test Query Format

The test queries file contains a set of search queries and expected results:

```json
[
  {
    "name": "Basic keyword search",
    "query": {
      "query": "baby shoes",
      "limit": 10
    },
    "expectations": {
      "min_results": 5,
      "max_results": 50,
      "expected_ids": ["prod1", "prod2"],
      "excluded_ids": ["prod99"]
    }
  },
  {
    "name": "Filtered search by age",
    "query": {
      "query": "toys",
      "filters": {
        "ageBucket": "1 to 3 years"
      },
      "limit": 10
    },
    "expectations": {
      "min_results": 3,
      "contains_terms": ["toy", "play"],
      "all_match_filter": true
    }
  }
]
```

### Testing Metrics

The search test script measures and reports:

1. **Relevance**: How well search results match the query intent
2. **Performance**: Response times for different query types
3. **Filtering**: Accuracy of faceted search and filtering
4. **Stability**: Consistency of results across multiple identical queries

## Vector Search Testing

To specifically test the vector search capabilities:

```bash
python scripts/test_vector_search.py \
  --api-url "http://localhost:8000" \
  --api-key "your_api_key" \
  --test-products "test_products.json"
```

This script:

1. Takes sample products
2. Generates queries based on their descriptions
3. Verifies the original products appear in search results
4. Tests semantic similarity by using synonyms and related terms
5. Compares vector search results with keyword search results

## Performance Testing

To evaluate system performance under load:

```bash
python scripts/load_test.py \
  --api-url "http://localhost:8000" \
  --api-key "your_api_key" \
  --duration 300 \
  --users 10 \
  --ramp-up 60
```

The load test measures:

- Requests per second (RPS) capacity
- Average response time
- Error rate under load
- Resource utilization (CPU, memory, network)

## Continuous Monitoring

After initial testing, implement continuous monitoring:

1. **Regular health checks**: Automated tests to verify API availability
2. **Search quality monitoring**: Track relevance metrics over time
3. **Performance tracking**: Monitor response times and resource utilization
4. **User feedback analysis**: Collect and analyze user search behaviors

## Search Quality Improvement

Based on testing results, improve search quality by:

1. **Index tuning**: Adjust weights and analyzers in MongoDB Atlas Search
2. **Query refinement**: Modify the search algorithm based on test results
3. **Data enrichment**: Add missing information to improve search relevance
4. **Synonym expansion**: Add domain-specific synonyms to improve recall

## Documentation

Maintain documentation of testing results:

- Baseline performance metrics
- Known limitations or edge cases
- Search quality improvements over time
- Configuration changes and their impact
