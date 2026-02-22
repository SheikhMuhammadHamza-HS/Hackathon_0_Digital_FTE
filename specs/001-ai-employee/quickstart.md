# AI Employee System - Quick Start Guide

**Version**: 1.0.0 | **Date**: 2025-02-21 | **Target**: Small Business (1-10 employees)

## Overview

The AI Employee system is a fully autonomous business operations assistant designed for small businesses. It handles invoicing, payment reconciliation, social media management, and CEO reporting with human oversight for financial operations.

## Prerequisites

### System Requirements
- **Operating System**: Linux (Ubuntu 20.04+) or Windows 10/11 with WSL2
- **Python**: 3.11 or higher
- **Memory**: Minimum 4GB RAM (8GB recommended)
- **Storage**: 10GB free space
- **Network**: Stable internet connection for API integrations

### External Services
- **Odoo Community Edition**: v15+ (localhost or remote)
- **Email Service**: SMTP server or SendGrid account
- **Social Media APIs**: Platform-specific developer accounts
  - X/Twitter API v2
  - Facebook Graph API
  - Instagram Basic Display API
  - LinkedIn APIs

## Installation

### 1. Clone Repository
```bash
git clone <repository-url>
cd ai_employee
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Configuration
```bash
cp .env.example .env
```

Edit `.env` with your configuration:
```env
# Odoo Configuration
ODOO_URL=http://localhost:8069
ODOO_DB=your_database
ODOO_USERNAME=your_username
ODOO_PASSWORD=your_password

# Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
EMAIL_FROM=AI Employee <noreply@yourcompany.com>

# Social Media APIs
TWITTER_API_KEY=your_twitter_api_key
TWITTER_API_SECRET=your_twitter_api_secret
TWITTER_ACCESS_TOKEN=your_access_token
TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret

FACEBOOK_PAGE_ID=your_page_id
FACEBOOK_ACCESS_TOKEN=your_page_access_token

INSTAGRAM_USER_ID=your_user_id
INSTAGRAM_ACCESS_TOKEN=your_access_token

LINKEDIN_CLIENT_ID=your_client_id
LINKEDIN_CLIENT_SECRET=your_client_secret

# System Configuration
LOG_LEVEL=INFO
DATA_RETENTION_DAYS=730
APPROVAL_TIMEOUT_HOURS=4
```

### 5. Initialize File Structure
```bash
# Create required directories
mkdir -p /Vault/Inbox /Vault/Needs_Action /Vault/Done /Vault/Logs
mkdir -p /Vault/Pending_Approval /Vault/Approved /Vault/Rejected
mkdir -p /Vault/Reports /Vault/Archive
```

### 6. Start the System
```bash
python main.py
```

## Initial Setup

### 1. Configure Odoo Integration
1. Access Odoo web interface
2. Create API user with appropriate permissions
3. Note down database name, URL, and credentials
4. Update `.env` file with Odoo configuration

### 2. Set Up Social Media Accounts
1. Apply for developer accounts on each platform
2. Create applications and obtain API keys
3. Configure OAuth callbacks and permissions
4. Update `.env` with API credentials

### 3. Configure Email Notifications
1. Set up SMTP server or SendGrid account
2. Create application-specific password if using Gmail
3. Test email configuration
4. Update `.env` with email settings

### 4. Create First Client (Optional)
```python
# Use the API to create your first client
curl -X POST http://localhost:8000/api/v1/clients \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Example Client",
    "email": "client@example.com",
    "address": "123 Main St, City, State 12345",
    "phone": "+1-555-0123"
  }'
```

## Daily Operations

### Invoice Workflow
1. **Client sends invoice request** → File appears in `/Vault/Inbox`
2. **AI processes request** → Creates draft invoice in Odoo
3. **Approval required** → File created in `/Vault/Pending_Approval`
4. **Human reviews** → Move file to `/Vault/Approved`
5. **AI posts invoice** → Invoice sent to client, file moved to `/Vault/Done`

### Payment Reconciliation
1. **Bank transaction detected** → AI matches to open invoices
2. **Draft payment created** → Requires approval for amounts >$100
3. **Human approves** → Payment reconciled in Odoo
4. **Client notified** → Receipt sent via email

### Social Media Management
1. **Content ready** → Schedule post for optimal time
2. **AI adapts content** → Platform-specific formatting applied
3. **Post published** → Monitor engagement and mentions
4. **Weekly report** → Metrics included in CEO briefing

### CEO Briefing
1. **Monday 8 AM** → Automatic briefing generation
2. **Data aggregated** → Financial, operational, social metrics
3. **Report delivered** → Emailed to CEO, saved in `/Vault/Reports`
4. **Suggestions provided** → Actionable business insights

## File-Based Approval System

### Directory Structure
```
/Vault/
├── Inbox/                 # Incoming requests
├── Needs_Action/          # Processing queue
├── Pending_Approval/      # Awaiting human review
├── Approved/             # Approved actions
├── Rejected/             # Rejected actions
├── Done/                 # Completed actions
├── Logs/                 # System logs
├── Reports/              # Generated reports
└── Archive/              # Old records
```

### Approval Process
1. **File appears in `/Vault/Pending_Approval`**
2. **File name format**: `{action}_{id}_{timestamp}.md`
3. **Review file content** → Contains all relevant details
4. **Decision**:
   - Move to `/Vault/Approved` to proceed
   - Move to `/Vault/Rejected` to cancel
   - Edit file to add notes before approval

### Approval File Example
```markdown
# Invoice Approval Request

**Invoice ID**: INV-2025-001
**Client**: Example Client
**Amount**: $1,250.00
**Due Date**: 2025-03-15

## Details
- Services: Consulting services (40 hours)
- Tax: 10% ($125.00)
- Total: $1,375.00

## Action Required
Move this file to `/Vault/Approved` to post the invoice to Odoo
Move this file to `/Vault/Rejected` to cancel this invoice

---
Generated: 2025-02-21 10:30:00
```

## Monitoring and Maintenance

### Health Checks
- **System status**: `GET /api/v1/health`
- **Service monitoring**: Automatic watchdog process
- **Error tracking**: Comprehensive logging in `/Vault/Logs`

### Log Management
- **Location**: `/Vault/Logs/`
- **Retention**: 2 years (configurable)
- **Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Rotation**: Daily log files with automatic cleanup

### Backup Procedures
1. **Database backup**: Odoo PostgreSQL backup
2. **File backup**: `/Vault` directory backup
3. **Configuration backup**: `.env` file backup
4. **Schedule**: Daily automated backups

## Troubleshooting

### Common Issues

#### Odoo Connection Failed
```bash
# Check Odoo status
curl http://localhost:8069/web/database/selector

# Verify credentials
python -c "from integrations.odoo_client import OdooClient; print(OdooClient().test_connection())"
```

#### Social Media API Errors
```bash
# Check API limits
curl -H "Authorization: Bearer $TOKEN" https://api.twitter.com/2/users/me

# Reset tokens if expired
# Follow platform-specific OAuth flow
```

#### File Permission Errors
```bash
# Fix directory permissions
chmod -R 755 /Vault/
chown -R $USER:$USER /Vault/
```

#### System Not Starting
```bash
# Check Python version
python --version

# Verify dependencies
pip check

# Check configuration
python -c "from core.config import Config; print(Config.validate())"
```

### Error Recovery
The system includes automatic error recovery with:
- **Circuit breaker**: Prevents cascade failures
- **Exponential backoff**: Retries transient errors
- **Fallback procedures**: Queues operations during downtime
- **Human alerts**: Notifies for critical issues

## Support

### Documentation
- **API Reference**: `/contracts/api.yaml`
- **Data Models**: `/data-model.md`
- **Architecture**: `/research.md`

### Getting Help
1. **Check logs**: `/Vault/Logs/` for error details
2. **Health check**: Verify system status
3. **Review configuration**: Ensure all `.env` settings are correct
4. **Contact support**: Provide logs and system details

## Next Steps

1. **Complete initial setup** following this guide
2. **Test with sample data** before production use
3. **Configure monitoring** and alerting preferences
4. **Schedule regular backups** and maintenance
5. **Train team members** on approval workflows

Congratulations! Your AI Employee system is now ready to automate your business operations.