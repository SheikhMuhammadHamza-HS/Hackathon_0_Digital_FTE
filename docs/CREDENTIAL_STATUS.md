# AI Employee - Credential Status

## ✅ Already Configured
- **SECRET_KEY**: Test-Secret-Key-12-Chars!
- **JWT_SECRET_KEY**: Test-JWT-Secret-12-Chars!
- **GEMINI_API_KEY**: Configured
- **GMAIL_TOKEN**: Configured with OAuth2 credentials
- **WHATSAPP_PHONE_NUMBER_ID**: Configured
- **WHATSAPP_ACCESS_TOKEN**: Configured

## ⚠️ Need Configuration for Real Testing

### Odoo ERP (Required for invoice testing)
```bash
ODOO_URL=http://localhost:8069          # Your Odoo instance URL
ODOO_DB=your_database_name              # Your database name
ODOO_USERNAME=your_username             # Your Odoo username
ODOO_PASSWORD=your_password             # Your Odoo password
```

### X/Twitter API
```bash
X_API_KEY=your_x_api_key
X_API_SECRET=your_x_api_secret
X_ACCESS_TOKEN=your_x_access_token
X_ACCESS_SECRET=your_x_access_secret
X_BEARER_TOKEN=your_x_bearer_token
```

### LinkedIn API
```bash
LINKEDIN_ACCESS_TOKEN=your_linkedin_access_token
LINKEDIN_USER_ID=your_linkedin_user_id
```

### Facebook/Instagram
```bash
FACEBOOK_ACCESS_TOKEN=your_facebook_access_token
FACEBOOK_PAGE_ID=your_facebook_page_id
INSTAGRAM_BUSINESS_ACCOUNT_ID=your_instagram_business_id
```

### Email Configuration
```bash
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
EMAIL_USE_TLS=true
```

## 🚀 Quick Start for Odoo Testing

1. **Install Odoo Community** (if not already):
   - Download from https://www.odoo.com/page/download
   - Or use Docker: `docker run -p 8069:8069 odoo:latest`

2. **Create Database**:
   - Open http://localhost:8069
   - Create new database (e.g., "test_db")
   - Remember admin password

3. **Update .env**:
   ```bash
   ODOO_URL=http://localhost:8069
   ODOO_DB=test_db
   ODOO_USERNAME=admin
   ODOO_PASSWORD=your_admin_password
   ```

4. **Test Connection**:
   ```bash
   python test_odoo_real.py
   ```

## 📝 Notes

- All credentials are in `.env` file
- `.env` is in `.gitignore` (not committed)
- DRY_RUN=true for safe testing
- Set DRY_RUN=false for real operations