---
name: odoo-integration
description: Connect to Odoo Community via JSON-RPC API for secure record management. Provides authentication, model operations (account.move, account.payment), and draft-only workflow with human approval requirements. Use when Claude needs to: (1) Create Odoo records in draft mode, (2) Read existing Odoo data, (3) Prepare entries for approval, (4) Integrate with other skills needing Odoo access
license: Complete terms in LICENSE.txt
---

# Odoo Integration

This skill provides secure JSON-RPC connectivity to Odoo Community (v19+) with draft-only operations and mandatory human approval workflows.

## Quick Start

Connect to Odoo:
```bash
/odoo-connect
```

Create draft invoice:
```bash
/odoo-create-invoice --partner "Customer Name" --lines "Service1:100,Service2:200"
```

Check approval status:
```bash
/odoo-check-approval INV-2024-001
```

## Prerequisites

### Environment Configuration
Required `.env` variables:
```bash
ODOO_URL=http://localhost:8069
ODOO_DB=your_db
ODOO_USERNAME=admin
ODOO_PASSWORD=your_password
```

### Odoo Requirements
- Odoo Community Edition v19+
- JSON-RPC endpoint accessible
- User has appropriate permissions
- Web Services enabled

## Core Capabilities

### 1. Authentication & Session Management

**Connection Process:**
1. Initialize JSON-RPC client
2. Authenticate with credentials
3. Establish session
4. Store session context

**Session Handling:**
```python
{
    "uid": 2,
    "session_id": "abc123...",
    "context": {
        "lang": "en_US",
        "tz": "UTC",
        "uid": 2
    }
}
```

### 2. Model Operations

**Supported Models:**
- `account.move` - Invoices/Bills
- `account.payment` - Payments
- `res.partner` - Customers/Vendors
- `account.journal` - Journals
- `product.product` - Products/Services

**Operations:**
- `search_read` - Query records
- `create` - Create new records (draft only)
- `write` - Update existing records
- `read` - Get record details

### 3. Draft-Only Workflow

**Mandatory Safety Rules:**
1. All records created in `draft` state
2. Never auto-post or confirm
3. Require approval file before posting
4. Log all operations

**Approval Process:**
```
1. Create draft record
2. Generate approval file in /Approved/
3. Wait for human approval
4. Execute posting (only after approval)
```

## Implementation Details

### JSON-RPC Client

**Connection Setup:**
```python
import requests
import json

class OdooClient:
    def __init__(self, url, db, username, password):
        self.url = url
        self.db = db
        self.username = username
        self.password = password
        self.uid = None
        self.session = None

    def authenticate(self):
        # Login to Odoo
        # Store session info
        # Return success/failure
```

### Helper Functions

**Create Invoice Draft:**
```python
def create_invoice_draft(partner_id, lines, journal_id):
    invoice_data = {
        'move_type': 'out_invoice',
        'partner_id': partner_id,
        'journal_id': journal_id,
        'invoice_line_ids': [(0, 0, line) for line in lines],
        'state': 'draft'
    }
    return odoo.create('account.move', invoice_data)
```

**Search Records:**
```python
def search_records(model, domain, fields=None):
    return odoo.execute_kw(
        model, 'search_read',
        [domain, fields or []]
    )
```

### Data Validation

**Required Fields Check:**
- Partner exists and is active
- Journal is configured
- Account codes are valid
- Dates are in correct format
- Amounts are positive numbers

**Business Rules:**
- Invoice dates not in the future
- Payment terms match partner settings
- Tax codes applicable
- Currency consistency

## File Structure

### Approval System
```
/Approved/
├── odoo-invoices/
│   ├── INV-2024-001.approved.md
│   └── INV-2024-002.approved.md
├── odoo-payments/
│   └── PAY-2024-001.approved.md
└── odoo-journals/
    └── journal-operations.approved.md
```

### Log Structure
```
/Vault/Logs/
└── odoo-operations-2024-01.md
```

**Log Entry Format:**
```markdown
## 2024-01-21 14:30 - Invoice Draft Created
- Operation: Create Invoice
- Model: account.move
- Record ID: 123
- Reference: INV-2024-001
- Amount: $500.00
- Status: Draft (pending approval)
- User: admin
```

## Commands Reference

### Connection Commands
```bash
# Test connection
/odoo-test-connection

# Authenticate
/odoo-authenticate

# Check session
/odoo-session-status
```

### Invoice Operations
```bash
# Create draft invoice
/odoo-create-invoice --partner "Acme Corp" --amount 1500

# Create with line items
/odoo-create-invoice --partner "Acme Corp" --lines "Consulting:1000,Development:500"

# Create with specific date
/odoo-create-invoice --partner "Acme Corp" --date 2024-01-31 --amount 1500

# Read invoice
/odoo-read-invoice INV-2024-001

# List draft invoices
/odoo-list-invoices --status draft
```

### Payment Operations
```bash
# Create payment draft
/odoo-create-payment --invoice INV-2024-001 --amount 1500

# Register payment
/odoo-register-payment --invoice INV-2024-001 --method bank

# List payments
/odoo-list-payments --status draft
```

### Approval Commands
```bash
# Check if approved
/odoo-check-approval INV-2024-001

# Post approved invoice
/odoo-post-invoice INV-2024-001 --approval-file /Approved/odoo-invoices/INV-2024-001.approved.md

# Create approval template
/odoo-create-approval INV-2024-001
```

## Approval File Format

### Invoice Approval Template
```markdown
---
operation: post_invoice
invoice_id: 123
invoice_ref: INV-2024-001
amount: 1500.00
partner: Acme Corp
approved_by: [Human Name]
approved_date: 2024-01-21
status: approved
---

# Invoice Approval Request

## Invoice Details
- **Reference:** INV-2024-001
- **Partner:** Acme Corp
- **Amount:** $1,500.00
- **Date:** 2024-01-21
- **Due:** 2024-02-20

## Line Items
| Description | Quantity | Price | Total |
|-------------|----------|-------|-------|
| Consulting | 10 hours | $100 | $1,000 |
| Development | 5 hours | $100 | $500 |

## Approval Checklist
- [ ] Invoice details verified
- [ ] Line items correct
- [ ] Tax calculations verified
- [ ] Payment terms confirmed
- [ ] Customer notified

## Approval
**Name:** _________________________
**Date:** _________________________
**Signature:** _________________________

---
Approved by: [Human Name]
This invoice is approved for posting in Odoo.
```

## Error Handling

### Connection Errors
- **Invalid credentials**: Check .env file
- **Database not found**: Verify ODOO_DB
- **Network timeout**: Check ODOO_URL
- **Version mismatch**: Verify Odoo v19+

### Data Errors
- **Missing partner**: Create partner first
- **Invalid journal**: Use valid journal ID
- **Wrong date format**: Use YYYY-MM-DD
- **Negative amounts**: Must be positive

### Validation Errors
```python
# Example validation
if invoice_date > today:
    raise ValueError("Invoice date cannot be in future")

if partner_credit_limit exceeded:
    raise ValueError("Partner credit limit exceeded")
```

## Security Considerations

1. **Credential Protection**
   - Never log passwords
   - Use environment variables only
   - Rotate credentials regularly

2. **Operation Safety**
   - Draft-only mode by default
   - Require approval for all postings
   - Log all modifications

3. **Access Control**
   - Limit user permissions
   - Use dedicated API user
   - Restrict model access

## Integration with Other Skills

### Invoice Generator Integration
```python
# From invoice-generator skill
def create_odoo_invoice(invoice_data):
    odoo_skill = get_skill('odoo-integration')
    return odoo_skill.create_invoice_draft(
        partner=invoice_data['client'],
        lines=invoice_data['items']
    )
```

### Payment Processing
```python
# For approved invoices
def process_payment(invoice_ref):
    if check_approval(invoice_ref):
        return post_invoice(invoice_ref)
    else:
        raise Error("Invoice not approved")
```

## Best Practices

1. **Always create drafts first**
2. **Verify data before submission**
3. **Use proper error handling**
4. **Maintain audit logs**
5. **Test in development environment**
6. **Backup before bulk operations**
7. **Monitor API rate limits**

## Troubleshooting

### Common Issues
1. **Connection refused**
   - Check Odoo is running
   - Verify port 8069 is open
   - Check firewall settings

2. **Authentication failed**
   - Verify credentials in .env
   - Check user is active
   - Reset password if needed

3. **Permission denied**
   - Grant required permissions
   - Check user groups
   - Verify access rights

4. **Create operation failed**
   - Check required fields
   - Verify data formats
   - Review validation rules

## API Reference

### Endpoints
- `/jsonrpc` - Main API endpoint
- `/web/session/authenticate` - Login
- `/web/dataset/call_kw` - Model operations

### Common Methods
```python
# Search
odoo.execute_kw(model, 'search', [domain])

# Read
odoo.execute_kw(model, 'read', [ids, fields])

# Create
odoo.execute_kw(model, 'create', [values])

# Write
odoo.execute_kw(model, 'write', [ids, values])

# Unlink (Delete)
odoo.execute_kw(model, 'unlink', [ids])
```

## Compliance Notes

- Follow Odoo licensing terms
- Respect data privacy laws
- Maintain audit trails
- Use secure connections
- Regular security updates
- Document all integrations