# Setup Guide

This guide provides detailed instructions for configuring the Personal AI Employee (Silver Tier) system.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Environment Configuration](#environment-configuration)
- [API Key Setup](#api-key-setup)
- [Folder Structure Setup](#folder-structure-setup)
- [Content Files Setup](#content-files-setup)
- [Validation](#validation)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Python Version
- Python 3.10 or higher
- pip package manager

### Verify Python Installation
```bash
python --version
# or
python3 --version
```

### Operating System Support
- Linux (Ubuntu, Debian, CentOS, etc.)
- macOS
- Windows 10/11 with WSL2 or native Python

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd hackathon_zero
```

### 2. Create Virtual Environment (Recommended)

```bash
# On Linux/macOS
python -m venv venv
source venv/bin/activate

# On Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Verify Installation

```bash
python -m pytest --version
# Should show pytest version
```

## Environment Configuration

### Create .env File

Copy the example environment file:
```bash
cp .env.example .env
```

### Environment Variables

Create or edit `.env` with the following variables:

#### Required Variables

```bash
# Google Gemini API Key (Primary AI provider)
GEMINI_API_KEY=your_gemini_api_key_here
```

#### Optional Variables

```bash
# Gmail API Key (for email monitoring)
GMAIL_API_KEY=your_gmail_api_key_here

# LinkedIn API Key (for LinkedIn posting)
LINKEDIN_API_KEY=your_linkedin_api_key_here

# Fallback API Key (for backward compatibility)
CLAUDE_CODE_API_KEY=your_claude_code_api_key_here
```

#### Path Configuration

```bash
# Input/Output Paths
INBOX_PATH=./Inbox
NEEDS_ACTION_PATH=./Needs_Action
PENDING_APPROVAL_PATH=./Pending_Approval
APPROVED_PATH=./Approved
DONE_PATH=./Done
FAILED_PATH=./Failed
LOGS_PATH=./Logs
VAULT_PATH=./Vault

# File Paths
DASHBOARD_PATH=./Dashboard.md
COMPANY_HANDBOOK_PATH=./Company_Handbook.md
BUSINESS_GOALS_PATH=./Business_Goals.md

# Configuration
FILE_SIZE_LIMIT=10485760
MAX_RETRY_ATTEMPTS=3
```

#### Logging Configuration

```bash
LOG_LEVEL=INFO
```

### Important Notes

1. **Never commit `.env` to version control**
2. **Keep `.env` file permissions restricted** (`chmod 600 .env` on Unix)
3. **Use strong, unique API keys**

## API Key Setup

### Google Gemini API Key (Recommended)

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API key"
4. Copy the API key
5. Add to `.env`:
   ```bash
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

### Gmail API Key (Optional)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Gmail API
4. Create credentials (OAuth 2.0 client ID)
5. Add to `.env`:
   ```bash
   GMAIL_API_KEY=your_gmail_api_key_here
   ```

### LinkedIn API Key (Optional)

1. Go to [LinkedIn Developer Portal](https://www.linkedin.com/developers/)
2. Create an application
3. Get API Key and Secret
4. Add to `.env`:
   ```bash
   LINKEDIN_API_KEY=your_linkedin_api_key_here
   ```

## Folder Structure Setup

### Create Required Folders

Run the setup command to create all required folders:
```bash
python -m src.cli.main setup
```

Or create manually:

```bash
mkdir -p Inbox
mkdir -p Needs_Action
mkdir -p Pending_Approval
mkdir -p Approved
mkdir -p Done
mkdir -p Failed
mkdir -p Logs
mkdir -p Vault
mkdir -p docs
mkdir -p scripts
```

### Folder Permissions

Ensure proper permissions on Linux/macOS:
```bash
chmod 755 Inbox Needs_Action Pending_Approval Approved Done Failed Logs Vault
chmod 600 .env
```

## Content Files Setup

### Company Handbook (`Company_Handbook.md`)

Create a file that defines email reply guidelines:

```markdown
# Company Handbook

## Email Reply Guidelines

### Tone
- Professional and friendly
- Clear and concise
- Helpful and solution-oriented

### Common Responses
- Acknowledgment: "Thank you for reaching out..."
- Escalation: "I'll escalate this to the appropriate team..."
- Closing: "Please let me know if you have any further questions..."

### Policy
- No sharing of confidential information
- Always respond within 24 hours
- Use proper grammar and spelling
```

### Business Goals (`Business_Goals.md`)

Create a file with business metrics and goals:

```markdown
# Business Goals

## Current Metrics
- Revenue: $1M
- Customers: 500
- Growth Rate: 15% QoQ

## Recent Achievements
- Launched new product feature
- Expanded to new market
- Hired 10 new team members

## Upcoming Initiatives
- Q1 Product Roadmap
- Customer satisfaction survey
- Marketing campaign launch
```

## Validation

### Run System Validation

Execute the validation script:
```bash
python scripts/validate_system.py
```

### Expected Output

```
System Validation
=================

[✓] Python version: 3.10+
[✓] Dependencies installed
[✓] Environment variables configured
[✓] Folders created
[✓] API keys valid (optional, if configured)
[✓] Dashboard initialized
[✓] Content files exist

Validation passed! System is ready.
```

### Manual Checks

1. **Check folder structure**:
   ```bash
   ls -la Inbox Needs_Action Pending_Approval Approved Done Failed Logs Vault
   ```

2. **Check content files**:
   ```bash
   cat Company_Handbook.md
   cat Business_Goals.md
   ```

3. **Check dashboard**:
   ```bash
   cat Dashboard.md
   ```

## Troubleshooting

### Common Issues

#### Issue: "ModuleNotFoundError"

**Solution**:
```bash
pip install -r requirements.txt
```

#### Issue: "API key not found"

**Solution**:
1. Check `.env` file exists
2. Verify API key is set correctly
3. Check file permissions

#### Issue: "Permission denied"

**Solution** (Linux/macOS):
```bash
chmod 755 Inbox Needs_Action Pending_Approval Approved Done Failed Logs Vault
chmod 600 .env
```

#### Issue: "Dashboard not updating"

**Solution**:
1. Check disk space
2. Verify file permissions
3. Check logs for errors

### Debug Mode

Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
python -m src.cli.main start
```

### Logs Location

Logs are stored in the `Logs/` directory with daily rotation:
```bash
ls -la Logs/
tail -f Logs/$(date +%Y-%m-%d).log
```

### Get Help

1. Check logs for error messages
2. Review this setup guide
3. Run validation script for diagnostics
4. Check [README.md](../README.md) for usage examples

## Security Best Practices

1. **Never share API keys publicly**
2. **Rotate API keys regularly**
3. **Use read-only API keys where possible**
4. **Limit API key scope to necessary permissions**
5. **Monitor API usage for anomalies**
6. **Keep system dependencies updated**
7. **Use HTTPS for all API calls**
8. **Implement rate limiting**

## Next Steps

After successful setup:

1. Run the validation script: `python scripts/validate_system.py`
2. Start the agent: `python -m src.cli.main start`
3. Create a test file in `Inbox/`
4. Check `Dashboard.md` for updates
5. Review logs in `Logs/` for activity

For usage instructions, see [README.md](../README.md).