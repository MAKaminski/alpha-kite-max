FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY ../../backend /app/backend

# Copy streaming service
COPY streaming_service.py .
COPY .env .

# Make streaming service executable
RUN chmod +x streaming_service.py

# Health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD pgrep -f streaming_service.py || exit 1

# Run streaming service
CMD ["python", "-u", "streaming_service.py"]

