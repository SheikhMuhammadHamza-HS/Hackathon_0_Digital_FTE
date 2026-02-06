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
