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

# Ensure the .env defaults to Cloud Node execution
ENV PLATINUM_MODE=cloud
ENV PYTHONPATH=/app

# Railway/Render will run this startup script that launches both Vault Sync and the Main Engine
CMD ["python", "scripts/cloud_startup.py"]
