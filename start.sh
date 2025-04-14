#!/bin/bash
# Start script for the MongoDB Atlas Search API

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Error: docker-compose is not installed. Please install docker-compose first."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "Please edit the .env file with your MongoDB Atlas credentials if needed."
fi

# Build and start the containers
echo "Building and starting containers..."
docker-compose up -d --build

# Wait for the containers to be ready
echo "Waiting for API to be ready..."
sleep 5

# Check if the API is healthy
echo "Checking API health..."
HEALTH_CHECK=$(curl -s http://localhost:8000/health)
if [[ $HEALTH_CHECK == *"healthy"* ]]; then
    echo "API is healthy and ready to use!"
    echo "API documentation available at: http://localhost:8000/docs"
    echo ""
    echo "Loading sample data (optional)..."
    echo "To load sample data, run: cd test_data && python load_test_data.py"
    echo ""
    echo "To stop the application, run: docker-compose down"
else
    echo "API is not responding. Please check the logs for issues:"
    echo "docker-compose logs -f app"
fi
