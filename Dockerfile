FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ./app /app/

# Expose the port
EXPOSE 8000

# Make startup script executable
RUN chmod +x /app/startup.sh

# Command to run the application with startup script
CMD ["/app/startup.sh"]
