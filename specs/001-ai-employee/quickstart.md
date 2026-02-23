# AI Employee System - Quick Start Guide

**Version**: 1.0.0 | **Date**: 2026-02-23 | **Target**: Small Business (1-10 employees)

## Overview

The AI Employee system is a fully autonomous business operations assistant designed for small businesses. It handles invoicing, payment reconciliation, social media management, and CEO reporting with human oversight for financial operations.

## Prerequisites

### System Requirements
- **Operating System**: Linux (Ubuntu 20.04+) or Windows 10/11 with WSL2 or macOS
- **Python**: 3.11 or higher (3.13 recommended)
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
git clone https://github.com/your-org/ai-employee.git
cd ai-employee
```

### 2. Create Virtual Environment
```bash
python -m venv venv
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

### 3. Install Dependencies
```bash
# Install core dependencies
pip install -r requirements.txt

# Install optional dependencies for full functionality
pip install -r requirements-optional.txt
```

### 4. Environment Configuration
```bash
cp ai_employee/.env.example ai_employee/.env
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
# Create required directories (adjust path for your OS)
# Linux/macOS:
mkdir -p ~/Vault/Inbox ~/Vault/Needs_Action ~/Vault/Done ~/Vault/Logs
mkdir -p ~/Vault/Pending_Approval ~/Vault/Approved ~/Vault/Rejected
mkdir -p ~/Vault/Reports ~/Vault/Archive

# Windows:
mkdir %USERPROFILE%\Vault\Inbox %USERPROFILE%\Vault\Needs_Action %USERPROFILE%\Vault\Done %USERPROFILE%\Vault\Logs
mkdir %USERPROFILE%\Vault\Pending_Approval %USERPROFILE%\Vault\Approved %USERPROFILE%\Vault\Rejected
mkdir %USERPROFILE%\Vault\Reports %USERPROFILE%\Vault\Archive
```

### 6. Verify Installation
```bash
# Test core functionality
cd ai_employee
python -c "from ai_employee.core.config import Config; print('Configuration OK')"

# Run health check
python -m ai_employee.utils.health_monitor
```

### 7. Start the System
```bash
# Start main system
python ai_employee/main.py

# Or start with API server
python ai_employee/api/server.py
```

### 8. Verify System Status
```bash
# Check system health
curl http://localhost:8000/api/v1/health

# Check available endpoints
curl http://localhost:8000/docs
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
```bash
# Use the API to create your first client
curl -X POST http://localhost:8000/api/v1/clients \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Example Client",
    "email": "client@example.com",
    "address": "123 Main St, City, State 12345",
    "phone": "+1-555-0123"
  }'

# Or use the Python client
python -c "
from ai_employee.domains.invoicing.services import InvoiceService
service = InvoiceService()
client = service.create_client(
    name='Example Client',
    email='client@example.com',
    address='123 Main St, City, State 12345',
    phone='+1-555-0123'
)
print(f'Client created: {client.id}')
"
```

## Daily Operations

### Invoice Workflow
1. **Client sends invoice request** → File appears in `~/Vault/Inbox`
2. **AI processes request** → Creates draft invoice in Odoo
3. **Approval required** → File created in `~/Vault/Pending_Approval`
4. **Human reviews** → Move file to `~/Vault/Approved`
5. **AI posts invoice** → Invoice sent to client, file moved to `~/Vault/Done`

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
3. **Report delivered** → Emailed to CEO, saved in `~/Vault/Reports`
4. **Suggestions provided** → Actionable business insights

### Running CEO Briefing Manually
```bash
# Generate current week briefing
python -c "
from ai_employee.domains.reporting.services import ReportService
from ai_employee.utils.briefing_scheduler import BriefingScheduler
service = ReportService()
scheduler = BriefingScheduler()
briefing = scheduler.generate_briefing()
print(briefing)
"
```

## Backup and Restore

### Automatic Backups
The system automatically creates backups:
- **Daily**: 2:00 AM (7-day retention)
- **Weekly**: Sunday 3:00 AM (4-week retention)
- **Monthly**: 1st of month 4:00 AM (1-year retention)

### Manual Backup
```bash
# Create immediate backup
curl -X POST http://localhost:8000/api/v1/backup/create \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "backup_type": "manual",
    "include_media": true,
    "encrypt": true,
    "comment": "Pre-maintenance backup"
  }'
```

### List Backups
```bash
# View all backups
curl -X GET http://localhost:8000/api/v1/backup/list \
  -H "Authorization: Bearer <token>"

# Check backup statistics
curl -X GET http://localhost:8000/api/v1/backup/statistics \
  -H "Authorization: Bearer <token>"
```

### Restore from Backup
⚠️ **Warning**: Restore overwrites existing data
```bash
curl -X POST http://localhost:8000/api/v1/backup/restore \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "backup_id": "backup_manual_20240123_143022",
    "restore_components": ["database", "config"],
    "force": true
  }'
```

### Backup Configuration
Add to `.env`:
```bash
# Backup Settings
BACKUP_DIRECTORY=backups
BACKUP_ENCRYPTION_ENABLED=true
AUTO_BACKUP_ENABLED=true
BACKUP_RETENTION_DAILY=7
BACKUP_RETENTION_WEEKLY=28
BACKUP_RETENTION_MONTHLY=365
```

## File-Based Approval System

### Directory Structure
```
~/Vault/ (or %USERPROFILE%\Vault on Windows)
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

### Configuration File Location
- **Linux/macOS**: `~/.config/ai-employee/config.yaml`
- **Windows**: `%APPDATA%\ai-employee\config.yaml`
- **Environment**: `ai_employee/.env` (overrides config file)

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
- **System status**: `GET http://localhost:8000/api/v1/health`
- **Service monitoring**: Automatic watchdog process
- **Error tracking**: Comprehensive logging in `~/Vault/Logs`
- **Circuit breaker status**: `GET http://localhost:8000/api/v1/circuit-breaker/status`

### Log Management
- **Location**: `~/Vault/Logs/` (or `%USERPROFILE%\Vault\Logs`)
- **Retention**: 2 years (configurable via `DATA_RETENTION_DAYS`)
- **Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Rotation**: Daily log files with automatic cleanup
- **Format**: Structured JSON for easy parsing

### Backup Procedures
1. **Database backup**: Odoo PostgreSQL backup
   ```bash
   pg_dump odoo_db > backup_$(date +%Y%m%d).sql
   ```
2. **File backup**: `~/Vault` directory backup
   ```bash
   tar -czf vault_backup_$(date +%Y%m%d).tar.gz ~/Vault/
   ```
3. **Configuration backup**: `.env` file backup
4. **Schedule**: Daily automated backups via cron/systemd timer

### Performance Monitoring
```bash
# Check system metrics
curl http://localhost:8000/api/v1/metrics

# View active services
curl http://localhost:8000/api/v1/services/status

# Check rate limiting status
curl http://localhost:8000/api/v1/rate-limits/status
```

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
python -c "from ai_employee.core.config import Config; print(Config.validate())"

# Check all services
python -m ai_employee.utils.health_monitor --verbose
```

#### API Server Issues
```bash
# Check if server is running
curl http://localhost:8000/api/v1/health

# Restart server
pkill -f "ai_employee.api.server"
python ai_employee/api/server.py

# Check logs
tail -f ~/Vault/Logs/api_server.log
```

#### Integration Test Failures
```bash
# Run all tests
python -m pytest tests/integration/ -v

# Run specific test suite
python -m pytest tests/integration/test_briefing_generation.py -v

# Check test coverage
python -m pytest --cov=ai_employee tests/
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

## Testing Your Installation

### 1. Run Integration Tests
```bash
# Test all core functionality
python -m pytest tests/integration/ -v

# Expected output: All tests should pass
# test_briefing_generation.py: 17/17 passed
# test_data_aggregation_fixed.py: 7/7 passed
# test_invoice_workflow.py: 5/5 passed
# test_social_media.py: 4/4 passed
```

### 2. Test CEO Briefing Generation
```bash
# Generate a test briefing
python -c "
from ai_employee.domains.reporting.services import ReportService
import datetime
service = ReportService()
briefing = service.generate_weekly_briefing(
    start_date=datetime.date(2026, 2, 17),
    end_date=datetime.date(2026, 2, 23)
)
print('Briefing generated successfully:', briefing.id)
"
```

### 3. Test Social Media Integration
```bash
# Test rate limiting
python -c "
from ai_employee.domains.social_media.rate_limiter import RateLimiter
limiter = RateLimiter()
print('Rate limiter initialized:', limiter.platforms)
"
```

## Next Steps

1. **Complete initial setup** following this guide
2. **Run integration tests** to verify all components work
3. **Test with sample data** before production use
4. **Configure monitoring** and alerting preferences
5. **Schedule regular backups** and maintenance
6. **Train team members** on approval workflows

## Production Deployment Checklist

- [ ] All integration tests passing
- [ ] Environment variables configured
- [ ] SSL certificates installed (for production)
- [ ] Backup procedures tested
- [ ] Monitoring and alerting configured
- [ ] User training completed
- [ ] Documentation reviewed

Congratulations! Your AI Employee system is now ready to automate your business operations.

## Additional Resources

- **API Documentation**: http://localhost:8000/docs
- **Monitoring Dashboard**: http://localhost:8000/dashboard
- **Architecture Guide**: `docs/architecture.md`
- **Troubleshooting Guide**: `docs/troubleshooting.md`
- **Community Support**: https://github.com/your-org/ai-employee/discussions