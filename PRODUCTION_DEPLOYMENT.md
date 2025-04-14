# Production Deployment Guide

This guide provides detailed instructions for deploying the MongoDB Atlas Search API to a production environment.

## Prerequisites

- MongoDB Atlas account with an M10 or higher tier cluster (for production workloads)
- Docker and Docker Compose installed on your production server
- Domain name (optional but recommended for production)
- TLS/SSL certificates for HTTPS (recommended for production)

## Step 1: Set Up MongoDB Atlas

1. Create a MongoDB Atlas cluster:
   - Choose a cloud provider and region close to your users
   - Select M10 or higher tier for production workloads
   - Enable backup and monitoring features

2. Configure security:
   - Create a dedicated database user with appropriate permissions
   - Restrict network access to only your application servers' IPs
   - Enable IP access lists
   - Enable database auditing

3. Set up the vector search index as described in `mongo_atlas_setup.md`
   - Ensure proper index configuration for optimal search performance
   - Configure index refresh rates based on your update frequency

## Step 2: Environment Configuration

1. Create a production `.env` file:

```bash
# Production MongoDB Atlas connection string
MONGODB_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/productdb?retryWrites=true&w=majority

# Strong API key for production
API_KEY=<generate-strong-random-key>

# Optional performance tuning parameters
CACHE_SIZE=2000
CACHE_TTL=3600
MAX_CONCURRENT_EMBEDDING_REQUESTS=10
```

2. Configure proper logging:
   - Set up log rotation and monitoring
   - Configure alert triggers for performance issues

## Step 3: Production Docker Setup

1. Create a production `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.prod
    ports:
      - "8000:8000"
    volumes:
      - ./app:/app
      - ./logs:/app/logs
    environment:
      - MONGODB_URI=${MONGODB_URI}
      - API_KEY=${API_KEY}
      - LOG_LEVEL=INFO
      - WORKERS=4
      - CACHE_SIZE=${CACHE_SIZE:-2000}
      - CACHE_TTL=${CACHE_TTL:-3600}
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d
      - ./nginx/ssl:/etc/nginx/ssl
      - ./nginx/logs:/var/log/nginx
    depends_on:
      - app
    restart: always

volumes:
  logs:
```

2. Create a production-optimized Dockerfile:

```dockerfile
FROM python:3.9-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Final stage - smaller image
FROM python:3.9-slim

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Copy application code
COPY ./app /app/

# Create log directory
RUN mkdir -p /app/logs && chmod 777 /app/logs

# Add a non-root user
RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -s /bin/bash appuser && \
    chown -R appuser:appuser /app

USER appuser

# Expose the port
EXPOSE 8000

# Command to run the application with Gunicorn
CMD ["gunicorn", "main:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--log-level", "info", "--log-file", "/app/logs/gunicorn.log"]
```

3. Configure Nginx for SSL and load balancing:

Create the directory:
```bash
mkdir -p ./nginx/conf.d
```

Create a configuration file `./nginx/conf.d/app.conf`:
```nginx
server {
    listen 80;
    server_name api.yourdomain.com;
    
    # Redirect HTTP to HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name api.yourdomain.com;
    
    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    
    # Proxy to FastAPI app
    location / {
        limit_req zone=api_limit burst=20 nodelay;
        
        proxy_pass http://app:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Cache static files
    location /static {
        expires 1d;
        add_header Cache-Control "public";
    }
    
    # Health check endpoint bypasses rate limiting
    location /health {
        proxy_pass http://app:8000/health;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Step 4: CI/CD Pipeline Setup

1. Create a GitHub Actions workflow file:

```yaml
name: Deploy to Production

on:
  push:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run tests
        run: |
          pytest app/tests/

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to production server
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.PRODUCTION_HOST }}
          username: ${{ secrets.PRODUCTION_USERNAME }}
          key: ${{ secrets.PRODUCTION_SSH_KEY }}
          port: ${{ secrets.PRODUCTION_SSH_PORT }}
          script: |
            cd /path/to/application
            git pull origin main
            docker-compose -f docker-compose.prod.yml down
            docker-compose -f docker-compose.prod.yml build --no-cache
            docker-compose -f docker-compose.prod.yml up -d
```

## Step 5: Performance Monitoring

1. Set up monitoring and alerting:
   - Configure Prometheus and Grafana for metrics collection
   - Set up alerting for performance degradation
   - Monitor cache hit/miss rates
   - Track API response times

2. Create a monitoring stack:
   - Add Prometheus and Grafana services to your docker-compose.yml
   - Configure metrics endpoints in the FastAPI app
   - Set up dashboards for key performance indicators

## Step 6: Production Launch Checklist

Before going live:

- [ ] Run load tests using the benchmark script
- [ ] Verify MongoDB Atlas search indices are properly configured
- [ ] Check that all environment variables are properly set
- [ ] Configure proper backup strategies for MongoDB Atlas
- [ ] Implement a rollback strategy
- [ ] Set up proper logging and monitoring
- [ ] Configure SSL certificates for secure communication
- [ ] Review API access controls and security

## Step 7: Scaling Strategies

As your application grows:

1. Horizontal Scaling:
   - Deploy multiple instances of the API behind a load balancer
   - Use MongoDB Atlas's sharding capabilities for database scaling

2. Caching Optimization:
   - Consider adding Redis for distributed caching
   - Implement more aggressive caching strategies

3. Search Optimization:
   - Fine-tune vector indexes based on usage patterns
   - Consider dedicated clusters for search operations

## Troubleshooting

Common issues and solutions:

1. Slow search performance:
   - Check MongoDB Atlas metrics dashboard
   - Review index configurations
   - Optimize embedding generation process

2. High memory usage:
   - Adjust cache sizes based on available memory
   - Monitor embedding model memory usage

3. Connection issues:
   - Check network configurations
   - Verify MongoDB Atlas connection strings
   - Check IP whitelisting in MongoDB Atlas

4. High CPU usage:
   - Consider scaling up worker count
   - Review embedding generation bottlenecks
   - Check for inefficient queries
