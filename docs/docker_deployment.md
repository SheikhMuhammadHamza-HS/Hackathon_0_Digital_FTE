# Docker Deployment Guide

This guide provides step-by-step instructions for deploying the AI Employee system using Docker and Docker Compose.

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- At least 4GB RAM
- 20GB free disk space

## Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/yourorg/ai-employee.git
cd ai-employee
```

### 2. Configure Environment
```bash
# Copy environment template
cp .env.docker .env

# Edit configuration
nano .env
```

### 3. Deploy
```bash
# Build and start all services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f
```

### 4. Access Application
- API: http://localhost:8000
- Documentation: http://localhost:8000/docs
- Dashboard: http://localhost:8000/dashboard

## Configuration

### Environment Variables (.env)

```bash
# Application Settings
SECRET_KEY=your-super-secret-key-here-min-32-chars
JWT_SECRET_KEY=your-jwt-secret-key-here-min-32-chars
ENVIRONMENT=production
DEBUG=false

# Database Configuration
POSTGRES_DB=aiemployee
POSTGRES_USER=aiemployee
POSTGRES_PASSWORD=secure-database-password
DATABASE_URL=postgresql://aiemployee:secure-database-password@db:5432/aiemployee

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=noreply@yourdomain.com

# Odoo Integration
ODOO_URL=https://your-odoo.com
ODOO_DATABASE=production
ODOO_USERNAME=api_user
ODOO_PASSWORD=api-password

# Backup Configuration
BACKUP_DIRECTORY=/app/backups
BACKUP_ENCRYPTION_ENABLED=true
BACKUP_ENCRYPTION_KEY=your-32-character-encryption-key
```

## Docker Compose Configuration

### Production Docker Compose

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.prod
    restart: unless-stopped
    environment:
      - DATABASE_URL=postgresql://aiemployee:${POSTGRES_PASSWORD}@db:5432/aiemployee
      - REDIS_URL=redis://redis:6379/0
    env_file:
      - .env
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./backups:/app/backups
      - vault_data:/app/vault
    depends_on:
      - db
      - redis
    networks:
      - ai_employee_network
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'

  db:
    image: postgres:15-alpine
    restart: unless-stopped
    environment:
      - POSTGRES_DB=aiemployee
      - POSTGRES_USER=aiemployee
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    networks:
      - ai_employee_network
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - ai_employee_network
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.25'

  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/ssl:ro
      - ./web/static:/var/www/static:ro
    depends_on:
      - app
    networks:
      - ai_employee_network
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.25'

  backup:
    build:
      context: .
      dockerfile: Dockerfile.backup
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./backups:/backups
      - ./data:/data:ro
    depends_on:
      - db
    networks:
      - ai_employee_network
    command: >
      sh -c "
      while true; do
        python backup_script.py
        sleep 86400
      done
      "

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local
  vault_data:
    driver: local

networks:
  ai_employee_network:
    driver: bridge
```

## Dockerfiles

### Production Dockerfile

```dockerfile
# Dockerfile.prod
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/backups /app/vault && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Expose port
EXPOSE 8000

# Run application
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120", "ai_employee.api.server:app"]
```

### Backup Dockerfile

```dockerfile
# Dockerfile.backup
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backup_script.py .
COPY ai_employee/ ai_employee/

CMD ["python", "backup_script.py"]
```

## Nginx Configuration

### nginx.conf
```nginx
events {
    worker_connections 1024;
}

http {
    upstream app {
        server app:8000;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

    server {
        listen 80;
        server_name localhost;

        # Security headers
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";

        # Static files
        location /static/ {
            alias /var/www/static/;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }

        # API endpoints
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Dashboard
        location /dashboard {
            proxy_pass http://app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Default
        location / {
            proxy_pass http://app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

## Deployment Commands

### Initial Deployment
```bash
# Build and start
docker compose -f docker-compose.prod.yml up -d --build

# Initialize database
docker compose -f docker-compose.prod.yml exec app python -m ai_employee.database.migrate

# Create admin user
docker compose -f docker-compose.prod.yml exec app python -c "
from ai_employee.core.auth import create_user
create_user('admin', 'admin@company.com', 'secure-password', role='admin')
"
```

### Updates
```bash
# Pull latest code
git pull

# Rebuild and restart
docker compose -f docker-compose.prod.yml up -d --build

# Check status
docker compose -f docker-compose.prod.yml ps
```

### Maintenance
```bash
# View logs
docker compose -f docker-compose.prod.yml logs -f app

# Execute commands
docker compose -f docker-compose.prod.yml exec app bash

# Database backup
docker compose -f docker-compose.prod.yml exec db pg_dump -U aiemployee aiemployee > backup.sql

# Restore database
docker compose -f docker-compose.prod.yml exec -T db psql -U aiemployee aiemployee < backup.sql
```

## Monitoring

### Health Checks
```bash
# Check all services
docker compose -f docker-compose.prod.yml ps

# Check app health
curl http://localhost/api/v1/health

# Check resource usage
docker stats
```

### Log Management
```bash
# View real-time logs
docker compose -f docker-compose.prod.yml logs -f

# Rotate logs
docker compose -f docker-compose.prod.yml exec app logrotate /etc/logrotate.d/ai-employee
```

## SSL/TLS Setup

### Using Let's Encrypt
```bash
# Create certbot container
docker run -it --rm \
  -v /etc/letsencrypt:/etc/letsencrypt \
  -v /var/lib/letsencrypt:/var/lib/letsencrypt \
  -p 80:80 \
  certbot/certbot certonly --standalone -d yourdomain.com

# Update nginx.conf to use SSL
# Add SSL certificate paths
```

### Self-signed Certificates
```bash
# Create SSL directory
mkdir -p nginx/ssl

# Generate certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/nginx.key \
  -out nginx/ssl/nginx.crt
```

## Multi-Stage Builds

### Optimized Dockerfile
```dockerfile
# Dockerfile.optimized
FROM python:3.11-slim as builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy from builder
COPY --from=builder /root/.local /root/.local

# Create app user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set environment
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy application
COPY . .

# Create directories
RUN mkdir -p /app/data /app/logs /app/backups && \
    chown -R appuser:appuser /app

USER appuser

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "ai_employee.api.server:app"]
```

## Production Best Practices

### 1. Resource Limits
```yaml
deploy:
  resources:
    limits:
      memory: 2G
      cpus: '1.0'
    reservations:
      memory: 1G
      cpus: '0.5'
```

### 2. Health Checks
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### 3. Restart Policies
```yaml
restart: unless-stopped
```

### 4. Logging
```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

## Troubleshooting

### Container Won't Start
```bash
# Check logs
docker compose logs app

# Check configuration
docker compose config

# Rebuild without cache
docker compose build --no-cache
```

### Database Connection Issues
```bash
# Check database container
docker compose exec db psql -U aiemployee -d aiemployee -c "SELECT 1;"

# Check network
docker network ls
docker network inspect ai-employee_ai_employee_network
```

### Performance Issues
```bash
# Monitor resources
docker stats

# Check container limits
docker inspect ai-employee_app_1
```

## Advanced Topics

### Docker Swarm Deployment
```yaml
# docker-stack.yml
version: '3.8'

services:
  app:
    image: your-registry/ai-employee:latest
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: on-failure
    networks:
      - ai_employee_network
```

Deploy with:
```bash
docker stack deploy -c docker-stack.yml ai-employee
```

### Kubernetes Deployment
```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-employee
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ai-employee
  template:
    metadata:
      labels:
        app: ai-employee
    spec:
      containers:
      - name: ai-employee
        image: your-registry/ai-employee:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

## Support

For Docker-specific issues:
1. Check Docker logs: `docker compose logs`
2. Verify configuration: `docker compose config`
3. Review resource usage: `docker stats`
4. Consult troubleshooting section

For additional help:
- Docker Documentation: https://docs.docker.com/
- Docker Compose Documentation: https://docs.docker.com/compose/
- GitHub Issues: https://github.com/yourorg/ai-employee/issues