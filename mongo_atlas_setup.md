# MongoDB Atlas Setup Instructions

This document provides detailed instructions for setting up MongoDB Atlas with vector search capabilities for this project.

## 1. Create MongoDB Atlas Cluster

1. Sign up or log in to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Create a new project (or use an existing one)
3. Create a new cluster:
   - Select a cloud provider and region (choose one close to your users)
   - Select a cluster tier (M0 Free tier is sufficient for testing)
   - Name your cluster (e.g., "product-search")

## 2. Configure Database Access

1. Create a database user:
   - Go to Security > Database Access
   - Add a new database user with password authentication
   - Grant read/write permissions to any database
   - Save the username and password for later use in your connection string

2. Configure network access:
   - Go to Security > Network Access
   - Add your IP address to the access list
   - For development, you can allow access from anywhere (0.0.0.0/0)

## 3. Create Vector Search Index

Vector search indexes must be created via the Atlas UI:

1. Go to your cluster and click on "Browse Collections"
2. Create a new database called "productdb" with a collection called "products"
3. Go to the "Search" tab
4. Click "Create Search Index"
5. Choose JSON Editor and input the following configuration:

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
      },
      "title": {
        "type": "string"
      },
      "description": {
        "type": "string"
      },
      "brand": {
        "type": "string"
      },
      "color": {
        "type": "string"
      },
      "ageBucket": {
        "type": "string"
      },
      "isOnSale": {
        "type": "boolean"
      },
      "seasons": {
        "type": "string"
      }
    }
  }
}
```

1. Name your index "product_search"
2. Click "Create Search Index"

## 4. Update Connection String

1. Go to your cluster and click "Connect"
2. Select "Connect your application"
3. Choose your driver (Python) and version (3.6 or later)
4. Copy the connection string
5. Replace `<username>`, `<password>`, and `<dbname>` with your actual values
6. Update the `.env` file with this connection string:

```env
MONGODB_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/productdb?retryWrites=true&w=majority
```

## 5. Test Vector Search

After connecting your application to MongoDB Atlas:

1. Load some test products using the provided script:

   ```bash
   cd test_data
   python load_test_data.py
   ```

2. Verify that vector search is working by testing a search query:

   ```bash
   curl -X POST http://localhost:8000/search \
     -H "Content-Type: application/json" \
     -H "x-apikey: dev_api_key_12345" \
     -d '{"query":"baby red shoes","filters":{},"limit":10,"offset":0}'
   ```

## Troubleshooting

- If vector search isn't working, ensure the index name in your code matches the one created in Atlas
- Check that the embedding dimensions match (384 for paraphrase-multilingual-MiniLM-L12-v2)
- Verify your MongoDB Atlas connection string is correct and contains the right database name
- Make sure your IP address is in the allowed list in Network Access
