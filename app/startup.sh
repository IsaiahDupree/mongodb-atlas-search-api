#!/bin/bash
set -e

# Startup script for our API in Docker
echo "Starting MongoDB Atlas Search API..."

# Display environment for debugging
echo "Environment:"
echo "MONGODB_URI=$MONGODB_URI"
echo "API_KEY=$API_KEY"

# Wait for MongoDB to be ready
echo "Waiting for MongoDB to be available..."
MAX_RETRIES=30
RETRIES=0

until nc -z mongodb 27017 || [ $RETRIES -eq $MAX_RETRIES ]; do
  echo "MongoDB is unavailable - waiting... (Attempt $RETRIES/$MAX_RETRIES)"
  sleep 2
  RETRIES=$((RETRIES+1))
done

if [ $RETRIES -eq $MAX_RETRIES ]; then
  echo "WARNING: Could not connect to MongoDB after $MAX_RETRIES attempts!"
  echo "Continuing anyway - application may fail if database is required"
else
  echo "MongoDB is available!"
fi

# List files for debugging
echo "Application files:"
ls -la

# Start the API server
echo "Starting the API server..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
