# Use official Python runtime as a parent image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install git (required for Vault Sync in the cloud)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Cloud environment settings
ENV PLATINUM_MODE=cloud
ENV PYTHONPATH=/app
ENV PORT=8000

# Start the FastAPI web server (Render Web Service)
CMD ["sh", "-c", "gunicorn ai_employee.api.server:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-8000}"]
