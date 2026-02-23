# Comprehensive Testing Guide

This guide explains how to thoroughly test all AI Employee system implementations to ensure everything works perfectly.

## Overview

The testing strategy covers all Phase 7 polish tasks:
- T075: Error handling
- T076: Performance optimization
- T078: Security hardening
- T079: Data retention
- T080: GDPR compliance
- T081: Monitoring dashboard
- T082: Backup and restore
- T083: System validation
- T084: Documentation

## Quick Test

### 1. Run Comprehensive Test Suite
```bash
# Make sure the API server is running
python ai_employee/api/server.py

# In another terminal, run tests
python test_implementation.py
```

### 2. Expected Output
```
✅ Error Classes: All custom error classes imported successfully
✅ 404 Error Handling: Proper 404 response returned
✅ Validation Error: Validation errors properly handled
✅ Cache Manager: Cache manager initialized
✅ Cache Operations: Cache set/get working
✅ Performance Monitor: Captured 1 metrics
✅ JWT Token Creation: Token created successfully
✅ JWT Token Validation: Token validated successfully
✅ Rate Limiting: Rate limiting working (allowed 5/7)
✅ XSS Prevention: XSS input sanitized
✅ Retention Policy Creation: Policy created successfully
✅ Retention Scheduling: Task scheduled: task_123
✅ Data Subject Registration: Subject registered: subject_456
✅ Consent Recording: Consent recorded successfully
✅ Right to Access: Data access granted
✅ Dashboard File: index.html: Exists (15420 bytes)
✅ Dashboard File: dashboard.css: Exists (8750 bytes)
✅ Dashboard File: dashboard.js: Exists (12300 bytes)
✅ Metric Collection: Collected metrics: ['cpu', 'memory', 'disk']
✅ Monitoring Health Endpoint: Health endpoint responding
✅ Backup Creation: Backup created: backup_test_20240223_143022
✅ Backup Listing: Found 1 backups
✅ Backup Verification: Backup integrity verified
✅ Backup Statistics API: Statistics endpoint working
✅ Documentation: Deployment Guide: Exists (25400 bytes, 650 lines)
✅ Documentation: Docker Deployment: Exists (18900 bytes, 480 lines)
✅ Documentation: AWS Deployment: Exists (32100 bytes, 820 lines)
✅ Documentation: Backup Guide: Exists (11509 bytes, 290 lines)
✅ Documentation: GDPR Guide: Exists (6915 bytes, 175 lines)
✅ Documentation: Security Guide: Exists (9921 bytes, 250 lines)
✅ Documentation: Deployment Checklist: Exists (8750 bytes, 220 lines)
✅ Documentation: Quickstart Guide: Exists (14614 bytes, 370 lines)

============================================================
TEST REPORT SUMMARY
============================================================

Total Tests: 29
✅ Passed: 29
❌ Failed: 0
⚠️  Warnings: 0

Success Rate: 100.0%

🎉 ALL TESTS PASSED!
The implementation is working perfectly!
```

## Detailed Testing Procedures

### 1. Error Handling Tests (T075)

#### Manual Tests
```bash
# Test 404 errors
curl -i http://localhost:8000/api/v1/nonexistent

# Test validation errors
curl -i -X POST http://localhost:8000/api/v1/clients \
  -H "Content-Type: application/json" \
  -d '{"name": "", "email": "invalid"}'

# Test rate limiting
for i in {1..10}; do
  curl -s http://localhost:8000/api/v1/health
done
```

#### Expected Results
- 404 returns proper JSON error with status code
- Validation errors return 400/422 with detailed messages
- Rate limiting blocks excessive requests

### 2. Performance Tests (T076)

#### Load Testing
```bash
# Install Apache Bench
sudo apt-get install apache2-utils

# Test API performance
ab -n 1000 -c 10 http://localhost:8000/api/v1/health

# Test with Python
python -c "
import asyncio
import aiohttp
import time

async def load_test():
    async with aiohttp.ClientSession() as session:
        tasks = []
        for _ in range(100):
            task = session.get('http://localhost:8000/api/v1/health')
            tasks.append(task)

        start = time.time()
        responses = await asyncio.gather(*tasks)
        end = time.time()

        success = sum(1 for r in responses if r.status == 200)
        print(f'Success: {success}/100, Time: {end-start:.2f}s')

asyncio.run(load_test())
"
```

#### Cache Testing
```python
# Test cache directly
python -c "
import asyncio
from ai_employee.utils.performance import CacheManager

async def test_cache():
    cache = CacheManager()

    # Test set/get
    await cache.set('key', 'value', ttl=60)
    result = await cache.get('key')
    print(f'Cache test: {result == \"value\"}')

    # Test expiration
    await cache.set('expire', 'test', ttl=1)
    await asyncio.sleep(2)
    result = await cache.get('expire')
    print(f'Expiration test: {result is None}')

asyncio.run(test_cache())
"
```

### 3. Security Tests (T078)

#### Authentication Tests
```bash
# Test JWT token
python -c "
from ai_employee.utils.security import TokenManager

tm = TokenManager()
token = tm.create_access_token({'user_id': 'test'})
print(f'Token: {token[:20]}...')

payload = tm.verify_token(token)
print(f'Valid: {payload is not None}')
print(f'User ID: {payload.get(\"user_id\") if payload else None}')
"
```

#### Security Headers Test
```bash
# Check security headers
curl -I http://localhost:8000/api/v1/health

# Expected headers:
# X-Frame-Options: DENY
# X-Content-Type-Options: nosniff
# X-XSS-Protection: 1; mode=block
```

#### Input Sanitization Test
```python
# Test XSS prevention
python -c "
from ai_employee.utils.security import InputValidator

validator = InputValidator()
xss = '<script>alert(\"xss\")</script>'
clean = validator.sanitize_input(xss)
print(f'Input: {xss}')
print(f'Output: {clean}')
print(f'Sanitized: {\"<script>\" not in clean}')
"
```

### 4. Data Retention Tests (T079)

#### Manual Retention Test
```python
# Test data retention
python -c "
import asyncio
from ai_employee.utils.data_retention import DataRetentionManager

async def test_retention():
    drm = DataRetentionManager()

    # Create policy
    policy = drm.create_policy(
        name='test_policy',
        retention_days=30,
        action='anonymize',
        data_type='user_data'
    )
    print(f'Policy created: {policy.name}')

    # Check active policies
    policies = drm.list_active_policies()
    print(f'Active policies: {len(policies)}')

asyncio.run(test_retention())
"
```

### 5. GDPR Tests (T080)

#### GDPR API Tests
```bash
# Register data subject
curl -X POST http://localhost:8000/api/v1/gdpr/data-subjects \
  -H "Content-Type: application/json" \
  -d '{
    "identifier": "test@example.com",
    "identifier_type": "email",
    "name": "Test User",
    "jurisdiction": "EU"
  }'

# Record consent
curl -X POST http://localhost:8000/api/v1/gdpr/data-subjects/{id}/consent \
  -H "Content-Type: application/json" \
  -d '{
    "purpose": "marketing",
    "granted": true,
    "legal_basis": "consent"
  }'

# Access data
curl -X GET http://localhost:8000/api/v1/gdpr/data-subjects/{id}/data

# Export data
curl -X GET http://localhost:8000/api/v1/gdpr/data-subjects/{id}/export
```

### 6. Monitoring Dashboard Tests (T081)

#### Dashboard Access
```bash
# Access dashboard
curl -I http://localhost:8000/dashboard

# Should return 200 with HTML content
```

#### Monitoring API Tests
```bash
# Health check
curl http://localhost:8000/api/v1/monitoring/health

# Metrics
curl http://localhost:8000/api/v1/monitoring/metrics

# Alerts
curl http://localhost:8000/api/v1/monitoring/alerts

# Performance data
curl http://localhost:8000/api/v1/monitoring/performance
```

#### Real-time Metrics Test
```python
# Test metrics collection
python -c "
import asyncio
from ai_employee.utils.monitoring import MonitoringDashboard

async def test_monitoring():
    monitor = MonitoringDashboard()

    # Collect metrics
    await monitor.collect_system_metrics()
    await monitor.collect_application_metrics()

    # Get summary
    summary = monitor.get_metrics_summary()
    print(f'Metrics: {list(summary.keys())}')
    print(f'CPU: {summary.get(\"cpu\", \"N/A\")}%')
    print(f'Memory: {summary.get(\"memory\", \"N/A\")}%')

asyncio.run(test_monitoring())
"
```

### 7. Backup and Restore Tests (T082)

#### Backup API Tests
```bash
# Create backup
curl -X POST http://localhost:8000/api/v1/backup/create \
  -H "Content-Type: application/json" \
  -d '{
    "backup_type": "manual",
    "include_media": false,
    "encrypt": false,
    "comment": "Test backup"
  }'

# List backups
curl http://localhost:8000/api/v1/backup/list

# Get statistics
curl http://localhost:8000/api/v1/backup/statistics
```

#### Backup Verification Test
```python
# Test backup integrity
python -c "
import asyncio
import tempfile
from ai_employee.utils.backup_manager import BackupManager

async def test_backup():
    # Create temp directory
    import os
    temp_dir = tempfile.mkdtemp()

    # Mock config
    class Config:
        BACKUP_DIRECTORY = os.path.join(temp_dir, 'backups')
        DATABASE_PATH = os.path.join(temp_dir, 'test.db')

    # Create backup
    bm = BackupManager()
    bm.config = Config()

    # Test backup creation
    result = await bm.create_backup(
        backup_type='test',
        include_media=False,
        encrypt=False
    )

    if result['status'] == 'success':
        # Test verification
        verify = await bm.verify_backup(result['backup_id'])
        print(f'Backup created: {result[\"backup_id\"]}')
        print(f'Verification: {verify[\"status\"]}')

    # Cleanup
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)

asyncio.run(test_backup())
"
```

### 8. End-to-End Integration Test

#### Full Workflow Test
```python
# test_full_workflow.py
import asyncio
import aiohttp
import json

async def full_workflow_test():
    """Test complete workflow"""
    async with aiohttp.ClientSession() as session:
        # 1. Health check
        async with session.get('http://localhost:8000/api/v1/health') as resp:
            assert resp.status == 200
            print("✅ Health check passed")

        # 2. Create client
        client_data = {
            "name": "Test Client",
            "email": "test@example.com",
            "address": "123 Test St",
            "phone": "+1-555-0123"
        }

        async with session.post('http://localhost:8000/api/v1/clients',
                               json=client_data) as resp:
            assert resp.status == 201
            client = await resp.json()
            client_id = client['id']
            print(f"✅ Client created: {client_id}")

        # 3. Create invoice
        invoice_data = {
            "client_id": client_id,
            "amount": 1000.00,
            "description": "Test Service",
            "due_date": "2024-02-28"
        }

        async with session.post('http://localhost:8000/api/v1/invoices',
                               json=invoice_data) as resp:
            assert resp.status == 201
            invoice = await resp.json()
            invoice_id = invoice['id']
            print(f"✅ Invoice created: {invoice_id}")

        # 4. Create backup
        backup_data = {
            "backup_type": "manual",
            "include_media": False,
            "encrypt": False,
            "comment": "E2E test backup"
        }

        async with session.post('http://localhost:8000/api/v1/backup/create',
                               json=backup_data) as resp:
            assert resp.status == 200
            backup = await resp.json()
            print(f"✅ Backup created: {backup['backup_id']}")

        # 5. Check monitoring
        async with session.get('http://localhost:8000/api/v1/monitoring/health') as resp:
            assert resp.status == 200
            health = await resp.json()
            print(f"✅ Monitoring health: {health['status']}")

        print("\n🎉 Full workflow test completed successfully!")

# Run the test
asyncio.run(full_workflow_test())
```

## Automated Testing with CI/CD

### GitHub Actions Workflow
```yaml
# .github/workflows/test.yml
name: Test Implementation

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt

    - name: Run tests
      run: |
        python test_implementation.py

    - name: Upload test report
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: test-report
        path: test_report.json
```

### Local Testing Script
```bash
#!/bin/bash
# test_all.sh - Comprehensive testing script

echo "🚀 Starting comprehensive testing..."

# Set environment
export SECRET_KEY="test-secret-key-for-testing-12chars"
export JWT_SECRET_KEY="test-jwt-secret-key-for-testing-12chars"
export ENVIRONMENT="test"

# Start API server in background
python ai_employee/api/server.py &
SERVER_PID=$!

# Wait for server to start
sleep 10

# Run comprehensive tests
python test_implementation.py
TEST_EXIT_CODE=$?

# Stop server
kill $SERVER_PID 2>/dev/null

# Generate additional reports
python -c "
import json
with open('test_report.json') as f:
    report = json.load(f)

print('='*60)
print('ADDITIONAL TEST METRICS')
print('='*60)
print(f'Test Timestamp: {report[\"timestamp\"]}')
print(f'Pass Rate: {report[\"summary\"][\"pass_rate\"]:.1f}%')
print(f'Total Tests: {report[\"summary\"][\"total\"]}')
print('='*60)
"

exit $TEST_EXIT_CODE
```

## Performance Benchmarks

### Expected Performance Metrics
- API response time: < 200ms (95th percentile)
- Database queries: < 100ms average
- Cache hit rate: > 90%
- Memory usage: < 512MB (idle)
- CPU usage: < 50% (normal load)

### Load Testing Targets
- 100 concurrent users
- 1000 requests/minute
- 99.9% uptime
- < 1% error rate

## Troubleshooting Test Failures

### Common Issues

1. **Import Errors**
```bash
# Solution: Check Python path and virtual environment
which python
python -c "import sys; print(sys.path)"
```

2. **Database Connection**
```bash
# Check database status
sudo systemctl status postgresql
psql -h localhost -U aiemployee -d aiemployee
```

3. **Port Conflicts**
```bash
# Check what's using port 8000
netstat -tulpn | grep 8000
lsof -i :8000
```

4. **Permission Errors**
```bash
# Check file permissions
ls -la ai_employee/
chmod 755 ai_employee/
```

5. **Memory Issues**
```bash
# Monitor memory
free -h
top -p $(pgrep -f ai_employee)
```

## Test Coverage Report

### Coverage Requirements
- Code coverage: > 80%
- Branch coverage: > 70%
- Function coverage: > 85%

### Running Coverage
```bash
# Install coverage
pip install coverage pytest-cov

# Run tests with coverage
pytest --cov=ai_employee tests/

# Generate report
coverage html
coverage report
```

## Continuous Monitoring

### Health Check Script
```bash
#!/bin/bash
# health_check.sh

API_URL="http://localhost:8000/api/v1/health"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $API_URL)

if [ $RESPONSE -eq 200 ]; then
    echo "✅ System healthy"
    exit 0
else
    echo "❌ System unhealthy (HTTP $RESPONSE)"
    # Send alert
    curl -X POST "$ALERT_WEBHOOK" \
        -H "Content-Type: application/json" \
        -d "{\"text\": \"AI Employee health check failed!\"}"
    exit 1
fi
```

### Cron Job for Automated Testing
```bash
# Add to crontab
0 */6 * * * /path/to/test_all.sh >> /var/log/test_results.log 2>&1
```

This comprehensive testing guide ensures all implementations work perfectly. Run the tests regularly to maintain system quality! 🎯