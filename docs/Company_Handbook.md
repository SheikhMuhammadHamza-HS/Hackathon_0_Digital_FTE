# Company Handbook

## Agent Behaviors

This document defines the rules and behaviors for the Digital FTE agent.

### Rules of Engagement

- **Politeness**: Always be polite in communications (Gmail/WhatsApp).
- **Spending**: Flag any payment over $500 for my manual approval.
- **Reporting**: Report any bottlenecks encountered during processing.

### File Processing Rules

1. **File Detection**: Monitor `/Inbox` for new files every 5 seconds
2. **File Types**: Process only supported file types (PDF, DOCX, TXT, XLSX, PPTX, JPG, PNG, GIF)
3. **Size Limit**: Reject files larger than 10MB
4. **Processing**: Create trigger in `/Needs_Action`, update dashboard, move to `/Done`
5. **Error Handling**: Retry failed processing up to 3 times with exponential backoff
6. **Security**: Log all file access for audit purposes

### Dashboard Updates

- Update dashboard in real-time when files are processed
- Show timestamp, filename, and processing status
- Track processing duration for performance monitoring

### Fallback Procedures

- If Claude Code API is unavailable, queue files for later processing
- Log all errors for diagnostic purposes
- Notify user if processing fails repeatedly

## Data Retention Policy

### Retention Periods
- **Logs**: All system logs kept for minimum 2 years
- **Invoices**: Invoice records retained for 2 years for tax compliance
- **Briefings**: CEO briefings archived for 2 years for historical reference
- **Approval Records**: All approval decisions kept for 2 years for audit purposes
- **Temporary Files**: Purged automatically after 7 days

### Data Purging
- System automatically removes temporary files after 7-day retention period
- Archive old records to compressed storage after 1 year
- Secure deletion of sensitive data after retention period expires
- Maintain index of purged records for compliance verification

### Compliance Notes
- 2-year retention meets standard business record requirements
- Temporary file cleanup prevents system storage overflow
- Audit trail maintained for full retention period
- Data access logged throughout retention lifecycle
