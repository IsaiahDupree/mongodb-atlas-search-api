# Data Overview

This document provides an overview of the source data structure and the target data model required by the MongoDB Atlas Search API.

## Source Data Structure

The source data is in a JSON file named `Omnium_Search_Products_START-1742999880951.json` with the following structure:

```json
{
  "totalHits": 26261,
  "result": [
    {
      "id": "4893156034908_no",
      "skuId": "4893156034908",
      "ean": "4893156034908",
      "productId": "4893156034908",
      "name": "Aktivitetspakke, Creepy Crawley Digging",
      "categories": [
        {
          "id": "f91ceed5-7fea-4e29-8d80-300b382da701_no",
          "categoryId": "f91ceed5-7fea-4e29-8d80-300b382da701",
          "name": "_Ukategoriserte (INNKJØP)",
          "parentId": "e63abab0-3e5b-453e-9348-a24b4f63b500",
          "language": "no",
          "isMainCategory": false,
          "isHidden": false,
          "sortIndex": 3
        },
        // Additional categories...
      ],
      "price": {
        "marketId": "b2b_nor",
        "unitPrice": 120.3,
        "currencyCode": "NOK",
        "discountAmount": 0.0,
        "discountPercent": 0.0,
        "originalUnitPrice": 120.3,
        // Additional price fields...
      },
      "prices": [
        // Different price points for various markets...
      ],
      "properties": [
        {
          "key": "SortimentCode",
          "value": "LS-liten",
          "keyGroup": "General"
        },
        // Additional properties...
      ],
      "tags": ["MISSING_NOR_TRANS"],
      "marketIds": ["b2b_nor"],
      "language": "no",
      // Additional metadata...
    },
    // Additional products...
  ]
}
```

### Key Fields in Source Data

- **id**: Unique identifier, typically EAN code + language suffix (e.g., "4893156034908_no")
- **skuId/ean**: Product identification codes
- **name**: Product name/title
- **categories**: Array of category objects with hierarchy information
- **price**: Primary price information
- **prices**: Array of price objects for different markets (b2b_nor, b2c_nor, b2c_swe)
- **properties**: Array of key-value pairs describing product attributes
- **tags**: Array of tag strings
- **marketIds**: Target markets for the product
- **language**: Language code (typically "no" for Norwegian)

## Target Data Model

The MongoDB Atlas Search API expects data in the following format, as defined in the `app/models/product.py` file:

```python
class Product(BaseModel):
    id: str
    title: str
    description: str
    brand: str
    imageThumbnailUrl: str = ""
    priceOriginal: float
    priceCurrent: float
    isOnSale: bool = False
    ageFrom: Optional[int] = None
    ageTo: Optional[int] = None
    ageBucket: Optional[str] = None  # e.g., "1 to 3 years"
    color: Optional[str] = None
    seasons: Optional[List[str]] = None  # e.g., ["winter", "spring"]
    productType: str = "main"  # main, part, extras
    seasonRelevancyFactor: float = 0.5  # 0 to 1 for boosting
    stockLevel: int = 0
```

When stored in MongoDB, two additional fields are added automatically during ingestion:

```python
class ProductInDB(Product):
    title_embedding: Optional[List[float]] = None
    description_embedding: Optional[List[float]] = None
    _id: Optional[str] = None
```

## Data Mapping Strategy

To transform the source data into the target model, we'll use the following mapping strategy:

| Target Field | Source Field | Transformation Notes |
|--------------|--------------|----------------------|
| id | id | Direct mapping |
| title | name | Direct mapping |
| description | Derived | Extract from properties if available, or generate placeholder |
| brand | properties | Find property with key "SupplierName" or similar |
| imageThumbnailUrl | N/A | Default empty string |
| priceOriginal | price.originalUnitPrice | Use b2c_nor market if available |
| priceCurrent | price.unitPrice | Use b2c_nor market if available |
| isOnSale | Derived | true if priceOriginal > priceCurrent |
| ageFrom | properties | Parse from appropriate property if available |
| ageTo | properties | Parse from appropriate property if available |
| ageBucket | Derived | Generate from ageFrom and ageTo if available |
| color | properties | Extract from properties if available |
| seasons | N/A | Default to null or derive from properties |
| productType | Derived | "main" by default |
| seasonRelevancyFactor | N/A | Default to 0.5 |
| stockLevel | availableInventory | Convert to int if available |

## Data Challenges and Considerations

1. **Missing Fields**: Many required fields in the target model may not be present in the source data and will need to be derived or given default values.

2. **Property Extraction**: The source data stores many attributes in a generic "properties" array, which will require parsing and extraction.

3. **Language Handling**: Source data has language suffixes in IDs which may need special handling.

4. **Price Selection**: Multiple price points exist for different markets, requiring a selection strategy.

5. **Category Handling**: The target model doesn't explicitly store categories, but they might be useful for search facets or filtering.

The transformation script will need to address these challenges to create valid data for ingestion.
