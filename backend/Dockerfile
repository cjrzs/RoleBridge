FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
# Handle network errors gracefully - try update, if fails continue anyway
RUN (apt-get update || true) && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy config.py from project root
COPY config.py /app/../config.py

# Copy application code
COPY backend/ .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

