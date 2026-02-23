# AI Employee Scripts

This directory contains all utility and test scripts organized by service.

## 📁 Folder Structure

### `/config`
- Configuration management scripts
- Environment file templates
- Setup utilities

### `/odoo`
- Odoo ERP integration tests
- Connection testing
- Invoice workflow tests

### `/gmail`
- Gmail API integration
- Email automation tests
- Token refresh utilities

### `/testing`
- All test suites
- Integration tests
- Verification scripts

### `/x`
- X/Twitter integration
- Social media posting tests

### `/ai_employee`
- Core AI employee utilities
- Helper functions
- Inspection tools

## 🚀 Usage

### Main Runner
```bash
# From project root
python scripts/run.py <service> <command>

# Examples
python scripts/run.py odoo test
python scripts/run.py gmail agent
python scripts/run.py testing core
```

### Individual Services
```bash
# Odoo
cd scripts/odoo
python run.py test

# Gmail
cd scripts/gmail
python run.py agent

# Testing
cd scripts/testing
python run.py invoice
```

## 📋 Available Commands

### Odoo
- `test` - Test Odoo connection
- `setup` - Configure Odoo credentials
- `update` - Update credentials

### Gmail
- `agent` - Run Gmail agent
- `debug` - Debug Gmail sending
- `refresh` - Refresh Gmail token

### Testing
- `core` - Core modules test
- `invoice` - Invoice workflow test
- `approval` - Approval detection test
- `simple` - Simple verification test

## ⚙️ Configuration

All configuration files are in `scripts/config/`:
- `.env` - Main environment file
- `.env.template` - Template with all variables
- `.env.test` - Test environment

## 🔧 Important Notes

1. Always run from project root or use the main runner
2. Keep DRY_RUN=true for safe testing
3. Check individual service folders for specific requirements
4. All paths are handled automatically by the runners