# Data Retention Guide

## Overview

The AI Employee system includes comprehensive data retention automation to enforce the 2-year data retention policy and ensure GDPR compliance. This guide covers the data retention features, configuration, and best practices.

## Data Retention Architecture

### Data Categories

The system categorizes data into different types, each with specific retention policies:

| Category | Default Retention | Default Action | Description |
|----------|------------------|----------------|-------------|
| **FINANCIAL** | 7 years (2555 days) | Archive | Invoices, payments, transactions |
| **OPERATIONAL** | 2 years (730 days) | Archive | Tasks, projects, reports |
| **COMMUNICATION** | 3 years (1095 days) | Archive | Emails, chat histories |
| **USER_DATA** | 1 year after deactivation | Anonymize | User preferences, settings |
| **AUDIT_LOGS** | 7 years (2555 days) | Archive | Security logs, access logs |
| **SYSTEM_LOGS** | 90 days | Delete | Application logs, debug info |
| **TEMPORARY** | 7 days | Delete | Temp files, cache, drafts |
| **BACKUP** | 1 year | Archive | System backups, DB dumps |

### Retention Actions

1. **KEEP**: Retain data indefinitely
2. **ARCHIVE**: Compress and move to archive storage
3. **DELETE**: Permanently remove data
4. **ANONYMIZE**: Remove personal identifiers

## Configuration

### Default Policies

The system comes with pre-configured retention policies that comply with common regulations:

```json
{
  "financial": {
    "retention_days": 2555,
    "action": "archive",
    "archive_location": "archives/financial",
    "compression": true
  },
  "operational": {
    "retention_days": 730,
    "action": "archive",
    "archive_location": "archives/operational",
    "compression": true
  }
}
```

### Custom Policies

You can create custom retention policies via the API:

```bash
curl -X POST http://localhost:8000/api/v1/retention/policies \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "category": "custom_data",
    "retention_days": 365,
    "action": "delete",
    "description": "Custom data retention policy"
  }'
```

### Policy Exceptions

Exclude specific paths from retention policies:

```bash
curl -X POST http://localhost:8000/api/v1/retention/policies \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "category": "operational",
    "retention_days": 730,
    "action": "archive",
    "exceptions": [
      "important_reports/",
      "legal_hold/"
    ]
  }'
```

## Automated Retention

### Scheduler

The retention scheduler runs automatically:

- **Frequency**: Daily at 2:00 AM
- **Scope**: All configured directories
- **Logging**: All actions are logged for audit

### Scheduled Directories

The system automatically scans these directories:

- `Vault/Logs/` - System logs
- `Vault/Reports/` - Operational reports
- `logs/` - Application logs
- `temp/` - Temporary files

### Manual Execution

Run retention policies manually:

```bash
# Dry run (no changes made)
curl -X POST http://localhost:8000/api/v1/retention/scheduler/run-now?dry_run=true \
  -H "Authorization: Bearer <token>"

# Execute policies
curl -X POST http://localhost:8000/api/v1/retention/scheduler/run-now \
  -H "Authorization: Bearer <token>"
```

## API Usage

### Managing Policies

#### List All Policies
```bash
curl -X GET http://localhost:8000/api/v1/retention/policies \
  -H "Authorization: Bearer <token>"
```

#### Get Specific Policy
```bash
curl -X GET http://localhost:8000/api/v1/retention/policies/financial \
  -H "Authorization: Bearer <token>"
```

#### Update Policy
```bash
curl -X POST http://localhost:8000/api/v1/retention/policies \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "category": "financial",
    "retention_days": 3000,
    "action": "archive"
  }'
```

#### Delete Policy
```bash
curl -X DELETE http://localhost:8000/api/v1/retention/policies/custom_data \
  -H "Authorization: Bearer <token>"
```

### Monitoring and Reporting

#### Get Retention Report
```bash
curl -X GET http://localhost:8000/api/v1/retention/report \
  -H "Authorization: Bearer <token>"
```

#### Get Statistics
```bash
curl -X GET http://localhost:8000/api/v1/retention/statistics \
  -H "Authorization: Bearer <token>"
```

#### View Retention Logs
```bash
curl -X GET http://localhost:8000/api/v1/retention/logs?limit=100 \
  -H "Authorization: Bearer <token>"
```

#### Scan Directory
```bash
curl -X GET "http://localhost:8000/api/v1/retention/scan?directory=Vault/Logs&category=system_logs" \
  -H "Authorization: Bearer <token>"
```

### Scheduler Management

#### Get Scheduler Status
```bash
curl -X GET http://localhost:8000/api/v1/retention/scheduler/status \
  -H "Authorization: Bearer <token>"
```

#### Start Scheduler
```bash
curl -X POST http://localhost:8000/api/v1/retention/scheduler/start \
  -H "Authorization: Bearer <token>"
```

#### Stop Scheduler
```bash
curl -X POST http://localhost:8000/api/v1/retention/scheduler/stop \
  -H "Authorization: Bearer <token>"
```

## Archive Management

### Archive Structure

Archives are organized by category:

```
archives/
├── financial/
│   ├── 2024/
│   │   ├── 01/
│   │   └── 02/
├── operational/
├── audit/
└── backups/
```

### Archive Compression

- Files are compressed using gzip
- Compression reduces storage by ~70%
- Original file structure is preserved
- Archives can be extracted with standard tools

### Accessing Archives

```bash
# Extract a gzipped archive
gunzip archive_file.gz

# List contents of tar.gz archive
tar -tzf archive.tar.gz

# Extract tar.gz archive
tar -xzf archive.tar.gz
```

## GDPR Compliance

### Data Subject Rights

The system supports GDPR compliance through:

1. **Right to Access**
   - All data can be exported via API
   - Comprehensive audit trail

2. **Right to Rectification**
   - Data can be updated through normal operations
   - Changes are logged

3. **Right to Erasure (Right to be Forgotten)**
   - Automatic deletion after retention period
   - Manual deletion capabilities
   - Anonymization option for required data

4. **Data Portability**
   - Export policies configuration
   - Export archived data on request

### Anonymization Process

When anonymizing data:
- Email addresses → anonymized@example.com
- Phone numbers → +1-555-000-0000
- Names → Anonymous User
- Addresses → [Empty]
- Other PII → Removed or masked

### Data Processing Records

All retention actions are logged:
```json
{
  "timestamp": "2026-02-23T02:00:00Z",
  "action": "archived",
  "item": {
    "path": "Vault/Reports/2024/report.pdf",
    "category": "operational",
    "size": 1024000
  },
  "destination": "archives/operational/2024/02/report.pdf.gz"
}
```

## Best Practices

### 1. Policy Configuration
- Review retention periods annually
- Consider legal requirements
- Document policy changes
- Test policies in dry-run mode first

### 2. Archive Management
- Regular backup of archives
- Monitor archive storage usage
- Implement off-site backup
- Test archive restoration

### 3. Monitoring
- Review retention logs weekly
- Monitor scheduler status
- Set up alerts for failures
- Track storage savings

### 4. Compliance
- Conduct annual retention audit
- Document retention procedures
- Train staff on data handling
- Maintain data processing records

## Troubleshooting

### Common Issues

#### Scheduler Not Running
```bash
# Check scheduler status
curl -X GET http://localhost:8000/api/v1/retention/scheduler/status

# Start scheduler
curl -X POST http://localhost:8000/api/v1/retention/scheduler/start
```

#### Policies Not Applying
```bash
# Check policy configuration
curl -X GET http://localhost:8000/api/v1/retention/policies

# Run manual execution with dry run
curl -X POST http://localhost:8000/api/v1/retention/scheduler/run-now?dry_run=true
```

#### Archive Access Issues
```bash
# Check archive directory
ls -la archives/

# Verify file permissions
chmod -R 644 archives/

# Test archive integrity
gunzip -t archive.gz
```

### Error Messages

#### "Policy not found"
- Check category spelling
- Verify policy exists
- Use GET /policies to list all

#### "Invalid category"
- Use valid categories from the list
- Check API documentation
- Case-sensitive category names

#### "Retention execution failed"
- Check system logs
- Verify directory permissions
- Ensure sufficient disk space

## Integration Examples

### Python Integration

```python
from ai_employee.utils.data_retention import retention_manager

# Apply policies programmatically
result = await retention_manager.apply_retention_policies(dry_run=True)
print(f"Would process {result['scanned']} items")
```

### Shell Script

```bash
#!/bin/bash
# Daily retention check

# Get scheduler status
STATUS=$(curl -s -X GET http://localhost:8000/api/v1/retention/scheduler/status \
  -H "Authorization: Bearer $TOKEN")

# Check if running
if [[ $STATUS == *"\"running\": false"* ]]; then
  echo "Starting retention scheduler"
  curl -X POST http://localhost:8000/api/v1/retention/scheduler/start \
    -H "Authorization: Bearer $TOKEN"
fi

# Get last run report
curl -X GET http://localhost:8000/api/v1/retention/report \
  -H "Authorization: Bearer $TOKEN" > retention_report_$(date +%Y%m%d).json
```

## Support

For data retention issues:
- Documentation: /docs/data_retention.md
- API Reference: /api/v1/retention/docs
- Logs: logs/retention.log
- Support: retention@company.com