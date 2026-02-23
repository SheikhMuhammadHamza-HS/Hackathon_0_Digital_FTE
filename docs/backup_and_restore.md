# Backup and Restore Guide

This guide covers the comprehensive backup and restore functionality of the AI Employee system.

## Overview

The AI Employee system includes enterprise-grade backup and restore capabilities with:
- Automated daily, weekly, and monthly backups
- Configurable retention policies
- Encrypted backup support
- Data integrity verification
- Selective restore capabilities
- Comprehensive logging and monitoring

## Configuration

### Environment Variables

```bash
# Backup Configuration
BACKUP_DIRECTORY=backups                    # Directory to store backups
BACKUP_ENCRYPTION_ENABLED=true              # Enable backup encryption
BACKUP_COMPRESSION_LEVEL=6                  # Compression level (1-9)
BACKUP_MAX_SIZE_GB=10                       # Maximum backup size in GB

# Retention Policies
BACKUP_RETENTION_DAILY=7                    # Keep daily backups for 7 days
BACKUP_RETENTION_WEEKLY=28                  # Keep weekly backups for 4 weeks
BACKUP_RETENTION_MONTHLY=365                # Keep monthly backups for 1 year

# Automatic Backup Scheduling
AUTO_BACKUP_ENABLED=true                    # Enable automatic backups
BACKUP_SCHEDULE_DAILY="0 2 * * *"          # Daily at 2 AM
BACKUP_SCHEDULE_WEEKLY="0 3 * * 0"         # Weekly on Sunday at 3 AM
BACKUP_SCHEDULE_MONTHLY="0 4 1 * *"        # Monthly on 1st at 4 AM
```

### Configuration File

Add to your `config.yaml`:

```yaml
backup:
  backup_directory: "backups"
  encryption_enabled: true
  compression_level: 6
  max_backup_size_gb: 10
  retention_days_daily: 7
  retention_days_weekly: 28
  retention_days_monthly: 365
  auto_backup_enabled: true
  backup_schedule_daily: "0 2 * * *"
  backup_schedule_weekly: "0 3 * * 0"
  backup_schedule_monthly: "0 4 1 * *"
```

## Using the Backup API

### Create a Backup

```bash
# Create a manual backup
curl -X POST "http://localhost:8000/api/v1/backup/create" \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "backup_type": "manual",
    "include_media": true,
    "encrypt": true,
    "comment": "Pre-maintenance backup"
  }'
```

Response:
```json
{
  "status": "success",
  "backup_id": "backup_manual_20240123_143022",
  "archive_path": "backups/backup_manual_20240123_143022.tar.gz.enc",
  "size_mb": 245.67,
  "checksum": "a1b2c3d4e5f6...",
  "metadata": {
    "type": "manual",
    "created_at": "2024-01-23T14:30:22",
    "includes_media": true,
    "encrypted": true
  }
}
```

### List Backups

```bash
# List all backups
curl -X GET "http://localhost:8000/api/v1/backup/list" \
  -H "Authorization: Bearer <your-token>"

# List only daily backups
curl -X GET "http://localhost:8000/api/v1/backup/list?backup_type=daily" \
  -H "Authorization: Bearer <your-token>"
```

### Verify Backup Integrity

```bash
curl -X GET "http://localhost:8000/api/v1/backup/verify/backup_manual_20240123_143022" \
  -H "Authorization: Bearer <your-token>"
```

Response:
```json
{
  "status": "success",
  "message": "Backup integrity verified",
  "metadata": {
    "backup_id": "backup_manual_20240123_143022",
    "type": "manual",
    "created_at": "2024-01-23T14:30:22",
    "checksums": {
      "database/ai_employee.db": "sha256:...",
      "configurations/config.yaml": "sha256:...",
      "user_data/vault/": "sha256:..."
    }
  }
}
```

### Restore from Backup

⚠️ **Warning**: Restore operations are destructive and will overwrite existing data.

```bash
curl -X POST "http://localhost:8000/api/v1/backup/restore" \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "backup_id": "backup_manual_20240123_143022",
    "restore_components": ["database", "config"],
    "force": true
  }'
```

Response:
```json
{
  "status": "success",
  "message": "Backup restored successfully",
  "restored_components": ["database", "config"],
  "results": {
    "database": {
      "status": "success",
      "message": "Database restored successfully"
    },
    "config": {
      "status": "success",
      "message": "Configurations restored successfully"
    }
  }
}
```

### Download Backup

```bash
curl -X GET "http://localhost:8000/api/v1/backup/download/backup_manual_20240123_143022" \
  -H "Authorization: Bearer <your-token>" \
  -o backup_manual_20240123_143022.tar.gz.enc
```

### Get Backup Statistics

```bash
curl -X GET "http://localhost:8000/api/v1/backup/statistics" \
  -H "Authorization: Bearer <your-token>"
```

Response:
```json
{
  "total_backups": 15,
  "total_size_mb": 2048.5,
  "oldest_backup": "2024-01-01T02:00:00",
  "newest_backup": "2024-01-23T14:30:22",
  "by_type": {
    "daily": {"count": 7, "size_mb": 1024.3},
    "weekly": {"count": 4, "size_mb": 512.1},
    "monthly": {"count": 3, "size_mb": 256.2},
    "manual": {"count": 1, "size_mb": 245.67}
  },
  "storage_path": "backups",
  "encryption_enabled": true
}
```

## Automatic Backup Scheduling

### Enable Automatic Backups

```bash
curl -X POST "http://localhost:8000/api/v1/backup/schedule/automatic" \
  -H "Authorization: Bearer <your-token>"
```

### Schedule Types

1. **Daily Backups**
   - Schedule: 2:00 AM every day
   - Retention: 7 days
   - Includes: Database, configurations, logs
   - Excludes: Media files

2. **Weekly Backups**
   - Schedule: 3:00 AM every Sunday
   - Retention: 4 weeks
   - Includes: Everything (database, configurations, logs, media, user data)

3. **Monthly Backups**
   - Schedule: 4:00 AM on the 1st of each month
   - Retention: 12 months
   - Includes: Everything

## Backup Components

Each backup contains the following components:

### Database
- SQLite database file
- SQL dump for human readability
- Includes all user data, tasks, and system metadata

### Configurations
- Main configuration file (`config.yaml`)
- Environment file template (`.env.template`)
- Skill configurations

### User Data
- Obsidian vault contents
- User preferences and settings
- Workspace data

### Logs
- Recent log files (last 30 days)
- Application logs
- Error logs

### Media (Optional)
- Attachments and media files
- Limited to files under 100MB
- Excluded from daily backups for size

## Security Considerations

### Encryption
- Backups are encrypted using Fernet symmetric encryption
- Encryption keys are stored in `backups/.backup_key`
- Key file has restricted permissions (600)

### Access Control
- Backup operations require `backup:manage` permission
- Restore operations require `system:admin` permission
- All API endpoints require authentication

### Integrity Verification
- SHA-256 checksums for all files
- Automatic verification before restore
- Registry tracks all backup metadata

## Best Practices

### 1. Regular Verification
- Verify backup integrity weekly
- Test restore procedures monthly
- Monitor backup success rates

### 2. Storage Management
- Monitor backup storage usage
- Adjust retention policies as needed
- Consider off-site storage for critical backups

### 3. Security
- Rotate encryption keys annually
- Restrict backup directory access
- Audit backup/restore operations

### 4. Disaster Recovery
- Maintain multiple backup copies
- Document restore procedures
- Test disaster recovery scenarios

## Troubleshooting

### Common Issues

#### Backup Creation Fails
1. Check disk space availability
2. Verify database is not locked
3. Check file permissions on backup directory
4. Review error logs for specific issues

#### Restore Fails
1. Verify backup integrity first
2. Check database permissions
3. Ensure sufficient disk space
4. Review component-specific errors

#### Automatic Backups Not Running
1. Verify scheduler is running
2. Check cron expressions are valid
3. Review system timezone settings
4. Check scheduler logs

### Error Messages

| Error | Cause | Solution |
|-------|--------|----------|
| "Backup directory does not exist" | Backup directory not created | Create backup directory and set permissions |
| "Database backup not found" | Source database missing | Check database path and permissions |
| "Checksum mismatch" | Backup corrupted | Delete backup and create new one |
| "Insufficient permissions" | User lacks required permission | Grant appropriate permissions |
| "Backup integrity check failed" | Backup corrupted or tampered | Delete backup and create new one |

## Monitoring and Logging

### Backup Logs
Location: `logs/backup.log`

```
2024-01-23 14:30:22 INFO Backup created successfully: backup_manual_20240123_143022
2024-01-23 14:30:22 INFO Backup size: 245.67 MB
2024-01-23 14:30:22 INFO Backup encrypted: true
2024-01-23 14:30:22 INFO Cleanup completed: removed 2 old backups
```

### Monitoring Dashboard
Access the monitoring dashboard at `/dashboard` to view:
- Backup success/failure rates
- Storage usage trends
- Next scheduled backup times
- Recent backup activity

## API Reference

### Endpoints

| Method | Endpoint | Description | Permissions |
|--------|----------|-------------|-------------|
| POST | `/api/v1/backup/create` | Create backup | backup:manage |
| GET | `/api/v1/backup/list` | List backups | backup:view |
| GET | `/api/v1/backup/verify/{id}` | Verify backup | backup:view |
| POST | `/api/v1/backup/restore` | Restore backup | system:admin |
| GET | `/api/v1/backup/statistics` | Get statistics | backup:view |
| DELETE | `/api/v1/backup/{id}` | Delete backup | backup:manage |
| GET | `/api/v1/backup/download/{id}` | Download backup | backup:view |
| POST | `/api/v1/backup/schedule/automatic` | Schedule backups | system:admin |

### Response Codes

- 200: Success
- 201: Created (for new backups)
- 400: Bad request
- 403: Forbidden (insufficient permissions)
- 404: Not found
- 500: Internal server error

## Integration Examples

### Python Script for Daily Backup

```python
import requests
import os

def create_daily_backup():
    """Create a daily backup via API"""
    token = os.getenv("BACKUP_API_TOKEN")
    url = "http://localhost:8000/api/v1/backup/create"

    data = {
        "backup_type": "daily",
        "include_media": False,
        "encrypt": True,
        "comment": "Automated daily backup"
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=data, headers=headers)

    if response.status_code == 200:
        result = response.json()
        print(f"Backup created: {result['backup_id']}")
        return result
    else:
        print(f"Backup failed: {response.text}")
        return None

if __name__ == "__main__":
    create_daily_backup()
```

### Bash Script for Backup Verification

```bash
#!/bin/bash

# Verify latest backup
API_URL="http://localhost:8000/api/v1/backup"
TOKEN="your-api-token"

# Get latest backup
LATEST_BACKUP=$(curl -s -H "Authorization: Bearer $TOKEN" \
  "$API_URL/list" | jq -r '.[0].backup_id')

if [ "$LATEST_BACKUP" != "null" ]; then
    echo "Verifying backup: $LATEST_BACKUP"

    RESULT=$(curl -s -H "Authorization: Bearer $TOKEN" \
      "$API_URL/verify/$LATEST_BACKUP")

    STATUS=$(echo $RESULT | jq -r '.status')

    if [ "$STATUS" == "success" ]; then
        echo "✓ Backup verified successfully"
    else
        echo "✗ Backup verification failed"
        echo $RESULT | jq -r '.message'
        exit 1
    fi
else
    echo "No backups found"
    exit 1
fi
```

## Support

For backup and restore issues:
1. Check the troubleshooting section
2. Review logs in `logs/backup.log`
3. Contact system administrator
4. Check monitoring dashboard for system status