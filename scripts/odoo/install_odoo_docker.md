# Install Odoo on Windows using Docker

## Prerequisites
- Docker Desktop installed
- Windows 10/11 with WSL2 enabled

## Quick Install Commands

### 1. Pull Odoo Image
```powershell
docker pull odoo:latest
```

### 2. Create Odoo Container
```powershell
docker run -d --name odoo ^
  -p 8069:8069 ^
  -e POSTGRES_DB=postgres ^
  -e POSTGRES_USER=odoo ^
  -e POSTGRES_PASSWORD=odoo ^
  -v odoo-data:/var/lib/odoo ^
  odoo:latest
```

### 3. Access Odoo
- Open browser: http://localhost:8069
- Create new database
- Complete setup

## Data Persistence
The `-v odoo-data:/var/lib/odoo` flag ensures your data persists even if container is removed.

## Docker Compose (Recommended for Development)
Create `docker-compose.yml`:
```yaml
version: '3.8'
services:
  odoo:
    image: odoo:latest
    container_name: odoo
    ports:
      - "8069:8069"
    environment:
      - POSTGRES_DB=postgres
      - POSTGRES_USER=odoo
      - POSTGRES_PASSWORD=odoo
    volumes:
      - odoo-data:/var/lib/odoo
    restart: unless-stopped
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=postgres
      - POSTGRES_USER=odoo
      - POSTGRES_PASSWORD=odoo
    volumes:
      - postgres-data:/var/lib/postgresql/data

# Run:
# docker-compose up -d
```

## Troubleshooting
- If port 8069 is busy, change to 8070
- If WSL2 issues, run: `wsl --update`
- For persistent issues, check Docker Desktop settings