# AI Employee System Deployment Guide

This guide provides comprehensive instructions for deploying the AI Employee system in production environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Configuration](#configuration)
4. [Deployment Options](#deployment-options)
5. [Production Deployment](#production-deployment)
6. [Monitoring and Maintenance](#monitoring-and-maintenance)
7. [Security Considerations](#security-considerations)
8. [Troubleshooting](#troubleshooting)
9. [Backup and Recovery](#backup-and-recovery)
10. [Scaling Guidelines](#scaling-guidelines)

## Prerequisites

### System Requirements

#### Minimum Requirements
- **CPU**: 2 cores
- **RAM**: 4GB
- **Storage**: 20GB SSD
- **OS**: Linux (Ubuntu 20.04+), Windows 10+, macOS 10.15+
- **Python**: 3.10 or higher

#### Recommended Requirements
- **CPU**: 4 cores
- **RAM**: 8GB
- **Storage**: 50GB SSD
- **OS**: Ubuntu 22.04 LTS
- **Python**: 3.11+

### Software Dependencies
- **Database**: SQLite 3.35+ (built-in) or PostgreSQL 13+
- **Web Server**: Nginx 1.18+ (recommended)
- **Process Manager**: systemd or supervisor
- **Reverse Proxy**: Nginx or Apache
- **SSL Certificate**: Let's Encrypt or commercial

### Network Requirements
- **Port 80**: HTTP (for SSL redirect)
- **Port 443**: HTTPS (primary)
- **Port 8000**: Application (internal)
- **Firewall**: Configured to allow necessary ports

## Environment Setup

### 1. Server Preparation

#### Ubuntu/Debian
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3.11 python3.11-venv python3-pip nginx postgresql postgresql-contrib

# Install node.js (for frontend assets)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Create application user
sudo useradd -m -s /bin/bash aiemployee
sudo usermod -aG sudo aiemployee
```

#### CentOS/RHEL
```bash
# Update system
sudo yum update -y

# Install EPEL repository
sudo yum install -y epel-release

# Install required packages
sudo yum install -y python3.11 python3-pip nginx postgresql-server postgresql-contrib

# Initialize PostgreSQL
sudo postgresql-setup initdb
sudo systemctl enable postgresql
sudo systemctl start postgresql
```

#### Windows Server
```powershell
# Install Python 3.11 from python.org
# Install PostgreSQL from postgresql.org
# Install Nginx for Windows
# Install NSSM for service management
```

### 2. Application Setup

#### Clone Repository
```bash
# Switch to application user
sudo su - aiemployee

# Clone the repository
git clone https://github.com/yourorg/ai-employee.git
cd ai-employee

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

#### Create Directory Structure
```bash
# Create required directories
mkdir -p logs data backups config
mkdir -p ~/Vault/{Inbox,Needs_Action,Pending_Approval,Approved,Rejected,Done,Logs,Reports,Archive}

# Set permissions
chmod 755 ~/Vault
chmod 755 ~/Vault/*
```

## Configuration

### 1. Environment Variables

Create `.env` file:
```bash
# Security Keys (CHANGE THESE!)
SECRET_KEY=your-super-secret-key-here-min-32-chars
JWT_SECRET_KEY=your-jwt-secret-key-here-min-32-chars

# Environment
ENVIRONMENT=production
DEBUG=false

# Database Configuration
DATABASE_URL=postgresql://aiemployee:password@localhost:5432/aiemployee
# Or for SQLite:
# DATABASE_PATH=/home/aiemployee/ai-employee/data/aiemployee.db

# API Configuration
API_HOST=127.0.0.1
API_PORT=8000
API_WORKERS=4

# SSL Configuration
SSL_CERT_PATH=/etc/letsencrypt/live/yourdomain.com/fullchain.pem
SSL_KEY_PATH=/etc/letsencrypt/live/yourdomain.com/privkey.pem

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
ODOO_PASSWORD=api_password

# Backup Configuration
BACKUP_DIRECTORY=/home/aiemployee/backups
BACKUP_ENCRYPTION_ENABLED=true
AUTO_BACKUP_ENABLED=true
BACKUP_RETENTION_DAILY=7
BACKUP_RETENTION_WEEKLY=28
BACKUP_RETENTION_MONTHLY=365

# Monitoring
SENTRY_DSN=your-sentry-dsn-here
LOG_LEVEL=INFO
```

### 2. Application Configuration

Create `config/production.yaml`:
```yaml
# Production Configuration
app:
  name: "AI Employee System"
  version: "1.0.0"
  environment: "production"

database:
  type: "postgresql"
  host: "localhost"
  port: 5432
  name: "aiemployee"
  user: "aiemployee"
  password: "${DATABASE_PASSWORD}"
  pool_size: 20
  max_overflow: 30

security:
  password_min_length: 12
  session_timeout: 3600
  max_login_attempts: 5
  lockout_duration: 900
  require_https: true

performance:
  cache_ttl_seconds: 3600
  max_concurrent_tasks: 20
  task_timeout_seconds: 300
  enable_compression: true

monitoring:
  metrics_enabled: true
  health_check_interval: 30
  alert_webhook: "${ALERT_WEBHOOK_URL}"
```

### 3. Database Setup

#### PostgreSQL
```bash
# Create database
sudo -u postgres createuser aiemployee
sudo -u postgres createdb aiemployee
sudo -u postgres psql -c "ALTER USER aiemployee PASSWORD 'your-password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE aiemployee TO aiemployee;"

# Run migrations
cd /home/aiemployee/ai-employee
source venv/bin/activate
python -m ai_employee.database.migrate
```

#### SQLite (for small deployments)
```bash
# Create database directory
mkdir -p data

# Initialize database
source venv/bin/activate
python -c "
from ai_employee.core.database import init_database
init_database()
"
```

## Deployment Options

### Option 1: Systemd Service (Recommended for Linux)

#### Create Service File
```bash
sudo nano /etc/systemd/system/aiemployee.service
```

```ini
[Unit]
Description=AI Employee System
After=network.target postgresql.service

[Service]
Type=exec
User=aiemployee
Group=aiemployee
WorkingDirectory=/home/aiemployee/ai-employee
Environment=PATH=/home/aiemployee/ai-employee/venv/bin
EnvironmentFile=/home/aiemployee/ai-employee/.env
ExecStart=/home/aiemployee/ai-employee/venv/bin/python -m ai_employee.api.server
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=10

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/home/aiemployee/ai-employee/data /home/aiemployee/ai-employee/logs /home/aiemployee/ai-employee/backups

[Install]
WantedBy=multi-user.target
```

#### Enable and Start Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable aiemployee
sudo systemctl start aiemployee
sudo systemctl status aiemployee
```

### Option 2: Docker Deployment

#### Create Dockerfile
```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create non-root user
RUN useradd -m -u 1000 aiemployee && chown -R aiemployee:aiemployee /app
USER aiemployee

# Expose port
EXPOSE 8000

# Run application
CMD ["python", "-m", "ai_employee.api.server"]
```

#### Create docker-compose.yml
```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://aiemployee:password@db:5432/aiemployee
      - SECRET_KEY=${SECRET_KEY}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
    depends_on:
      - db
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./backups:/app/backups
    restart: unless-stopped

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=aiemployee
      - POSTGRES_USER=aiemployee
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/letsencrypt
    depends_on:
      - app
    restart: unless-stopped

volumes:
  postgres_data:
```

#### Deploy with Docker
```bash
# Build and start
docker-compose up -d

# Check logs
docker-compose logs -f

# Stop
docker-compose down
```

### Option 3: Kubernetes Deployment

#### Create namespace
```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ai-employee
```

#### Create deployment
```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-employee
  namespace: ai-employee
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
              name: ai-employee-secrets
              key: database-url
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: ai-employee-secrets
              key: secret-key
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

## Production Deployment

### 1. Nginx Configuration

#### Create Nginx Config
```bash
sudo nano /etc/nginx/sites-available/ai-employee
```

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;

    # Security Headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";

    # Logging
    access_log /var/log/nginx/ai-employee.access.log;
    error_log /var/log/nginx/ai-employee.error.log;

    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

    # API Proxy
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    # Dashboard
    location /dashboard {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static Files
    location /static/ {
        alias /home/aiemployee/ai-employee/ai_employee/web/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # File Upload Size
    client_max_body_size 100M;
}
```

#### Enable Site
```bash
sudo ln -s /etc/nginx/sites-available/ai-employee /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 2. SSL Certificate Setup

#### Using Let's Encrypt
```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Setup auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### 3. Log Rotation

#### Create Logrotate Config
```bash
sudo nano /etc/logrotate.d/ai-employee
```

```
/home/aiemployee/ai-employee/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 aiemployee aiemployee
    postrotate
        systemctl reload aiemployee
    endscript
}
```

## Monitoring and Maintenance

### 1. Health Checks

#### Create Health Check Script
```bash
#!/bin/bash
# /home/aiemployee/scripts/health_check.sh

API_URL="https://yourdomain.com/api/v1/health"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $API_URL)

if [ $RESPONSE -ne 200 ]; then
    echo "Health check failed with status $RESPONSE"
    # Send alert
    curl -X POST "$ALERT_WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -d "{\"text\": \"AI Employee health check failed! Status: $RESPONSE\"}"
    exit 1
fi

echo "Health check passed"
```

#### Setup Cron Job
```bash
# Edit crontab
crontab -e

# Add health check every 5 minutes
*/5 * * * * /home/aiemployee/scripts/health_check.sh
```

### 2. Monitoring Setup

#### Prometheus Configuration
```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'ai-employee'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/api/v1/monitoring/metrics'
    scrape_interval: 30s
```

#### Grafana Dashboard
- Import AI Employee dashboard
- Monitor key metrics:
  - API response times
  - Error rates
  - Database connections
  - System resources

### 3. Backup Automation

#### Create Backup Script
```bash
#!/bin/bash
# /home/aiemployee/scripts/backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/aiemployee/backups"
LOG_FILE="/home/aiemployee/logs/backup.log"

echo "[$DATE] Starting backup" >> $LOG_FILE

# Create backup via API
curl -X POST "http://localhost:8000/api/v1/backup/create" \
    -H "Authorization: Bearer $BACKUP_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "backup_type": "daily",
        "include_media": true,
        "encrypt": true,
        "comment": "Automated daily backup"
    }' >> $LOG_FILE 2>&1

echo "[$DATE] Backup completed" >> $LOG_FILE
```

## Security Considerations

### 1. Firewall Configuration

#### UFW (Ubuntu)
```bash
# Enable firewall
sudo ufw enable

# Allow SSH
sudo ufw allow ssh

# Allow HTTP/HTTPS
sudo ufw allow 80
sudo ufw allow 443

# Deny other ports
sudo ufw default deny incoming
sudo ufw default allow outgoing
```

### 2. Application Security

#### Security Headers
Ensure all security headers are configured:
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- X-XSS-Protection
- Strict-Transport-Security
- Content-Security-Policy

#### Rate Limiting
Configure rate limits:
- API endpoints: 10 requests/second
- Authentication: 5 requests/minute
- File uploads: 1 request/second

### 3. Database Security

#### PostgreSQL
```sql
-- Create read-only user for reporting
CREATE USER readonly WITH PASSWORD 'secure-password';
GRANT CONNECT ON DATABASE aiemployee TO readonly;
GRANT USAGE ON SCHEMA public TO readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly;

-- Revoke unnecessary permissions
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON DATABASE aiemployee FROM PUBLIC;
```

## Troubleshooting

### Common Issues

#### 1. Service Won't Start
```bash
# Check logs
sudo journalctl -u aiemployee -f

# Check configuration
sudo -u aiemployee /home/aiemployee/ai-employee/venv/bin/python -m ai_employee.api.server --config-check
```

#### 2. Database Connection Failed
```bash
# Test connection
psql -h localhost -U aiemployee -d aiemployee

# Check PostgreSQL status
sudo systemctl status postgresql
```

#### 3. High Memory Usage
```bash
# Monitor processes
top -u aiemployee

# Check worker count
ps aux | grep "ai_employee.api.server" | wc -l

# Adjust workers in config
```

#### 4. SSL Certificate Issues
```bash
# Check certificate expiry
sudo certbot certificates

# Force renewal
sudo certbot renew --force

# Test Nginx config
sudo nginx -t
```

### Log Locations
- Application logs: `/home/aiemployee/ai-employee/logs/`
- Nginx logs: `/var/log/nginx/`
- System logs: `sudo journalctl -u aiemployee`

## Backup and Recovery

### 1. Automated Backups

#### Backup Schedule
- **Daily**: 2:00 AM, keep 7 days
- **Weekly**: Sunday 3:00 AM, keep 4 weeks
- **Monthly**: 1st 4:00 AM, keep 12 months

#### Off-site Backup
```bash
# Setup rsync to remote server
rsync -avz -e ssh /home/aiemployee/backups/ backup-server:/backups/ai-employee/

# Or use cloud storage
aws s3 sync /home/aiemployee/backups/ s3://your-backup-bucket/ai-employee/
```

### 2. Recovery Procedures

#### Full System Recovery
```bash
# 1. Stop services
sudo systemctl stop aiemployee nginx

# 2. Restore database
pg_restore -h localhost -U aiemployee -d aiemployee backup.sql

# 3. Restore application files
tar -xzf app_backup.tar.gz -C /home/aiemployee/

# 4. Start services
sudo systemctl start aiemployee nginx

# 5. Verify
curl -f https://yourdomain.com/api/v1/health
```

## Scaling Guidelines

### 1. Vertical Scaling

#### When to Scale Up
- CPU usage > 80%
- Memory usage > 80%
- Response times > 2 seconds

#### Scaling Steps
```bash
# 1. Increase resources
# 2. Adjust worker count
# 3. Increase database pool size
# 4. Add cache
```

### 2. Horizontal Scaling

#### Load Balancer Setup
```nginx
upstream ai_employee_backend {
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
}

server {
    location /api/ {
        proxy_pass http://ai_employee_backend;
    }
}
```

#### Database Scaling
- Read replicas for reporting
- Connection pooling
- Query optimization
- Index optimization

### 3. Caching Strategy

#### Redis Configuration
```python
# In config.yaml
cache:
  type: "redis"
  host: "localhost"
  port: 6379
  db: 0
  ttl: 3600
```

## Maintenance Tasks

### Daily
- Check system health
- Review error logs
- Verify backups

### Weekly
- Update security patches
- Review performance metrics
- Clean old logs

### Monthly
- Update dependencies
- Security audit
- Capacity planning

### Quarterly
- Disaster recovery test
- Performance tuning
- Documentation update

## Support and Resources

### Documentation
- [API Documentation](https://yourdomain.com/docs)
- [User Guide](docs/user_guide.md)
- [Troubleshooting](docs/troubleshooting.md)

### Community
- GitHub Issues
- Slack Channel
- Stack Overflow

### Professional Support
- Email: support@company.com
- Phone: +1-555-0123
- Support Portal: https://support.company.com

---

This deployment guide covers all aspects of deploying the AI Employee system in production. For additional help, refer to the troubleshooting section or contact support.