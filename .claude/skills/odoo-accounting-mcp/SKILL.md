---
name: odoo-accounting-mcp
description: Generate and manage invoices inside Odoo Community with client integration, approval workflows, and file management. Depends on odoo-integration skill. Use when Claude needs to: (1) Create Odoo invoices from Needs_Action files, (2) Generate approval requests for invoice posting, (3) Post approved invoices to Odoo, (4) Manage invoice lifecycle and file movements
license: Complete terms in LICENSE.txt
---

# Odoo Accounting MCP

This skill manages the complete invoice lifecycle within Odoo Community, integrating with client files, managing approvals, and maintaining audit trails.

## Dependencies

This skill requires:
- `odoo-integration` skill for Odoo connectivity
- Proper .env configuration for Odoo access
- Existing client files in `/Vault/Clients/`

## Quick Start

Process invoice from Needs_Action:
```bash
/odoo-invoice-process --file "Needs_Action/invoice-clientA-2024-01-21.md"
```

Check approval status:
```bash
/odoo-invoice-approval-check --client "Client A" --date 2024-01-21
```

Post approved invoice:
```bash
/odoo-invoice-post --approval-file "/Approved/INVOICE_ClientA_2024-01-21.md"
```

## Core Workflow

### 1. Invoice Creation Process

**Input Requirements:**
- Client file in `/Vault/Clients/<client>.md`
- Task file in `/Needs_Action/` with invoice details
- Valid rates from `/Vault/Accounting/Rates.md`

**Creation Steps:**
1. Read client information from file
2. Parse invoice details from Needs_Action file
3. Validate data and calculate totals
4. Create draft invoice in Odoo
5. Generate approval request file
6. Log operation

### 2. Approval Management

**HITL Rules (Human-in-the-Loop):**
- **NEVER** post invoice without `/Approved` file
- Payments > $100 always require approval
- New payees always require approval
- All invoices require approval regardless of amount

**Approval Process:**
```
1. Create approval file in /Pending_Approval/
2. Human reviews and moves to /Approved/
3. System detects approval and posts to Odoo
4. Update file locations and log completion
```

### 3. File Management

**File Movement Logic:**
```
/Needs_Action/invoice-<client>-<date>.md
    ↓ (Process)
/Pending_Approval/INVOICE_<client>_<date>.md
    ↓ (Human approval)
/Approved/INVOICE_<client>_<date>.md
    ↓ (Post to Odoo)
/Done/invoice-<client>-<date>.md
```

## Implementation Details

### Client File Structure

**Expected Format (`/Vault/Clients/<client>.md`):**
```markdown
---
name: Client A
odoo_partner_id: 1234
payment_terms: 30
tax_id: 12-3456789
default_journal: Sales
---

# Client A

**Address:** 123 Main St, City, State
**Contact:** John Doe
**Email:** john@clienta.com
**Phone:** 555-0123

## Billing Information
- **Payment Terms:** Net 30
- **Tax Rate:** 10%
- **Currency:** USD
```

### Needs_Action File Format

**Expected Format (`/Needs_Action/invoice-<client>-<date>.md`):**
```markdown
---
client: Client A
date: 2024-01-21
period: 2024-01
due_date: 2024-02-20
priority: normal
---

# Invoice Request - Client A

## Services Rendered
- Web Development: 40 hours @ $100/hour
- Consulting: 10 hours @ $150/hour
- Support Package: $500

## Notes
- Project completed on schedule
- Additional hours approved by client
```

### Approval File Generation

**Generated File (`/Pending_Approval/INVOICE_<client>_<date>.md`):**
```markdown
---
type: approval_request
action: post_invoice
client: Client A
amount: 6000.00
odoo_invoice_id: INV/2026/0001
odoo_draft_id: 567
status: pending
request_date: 2024-01-21
requested_by: claude
---

# Invoice Approval Request

## Invoice Details
- **Client:** Client A
- **Invoice Number:** INV/2026/0001
- **Amount:** $6,000.00
- **Date:** 2024-01-21
- **Due:** 2024-02-20
- **Odoo Draft ID:** 567

## Line Items
| Description | Quantity | Rate | Amount |
|-------------|----------|------|--------|
| Web Development | 40h | $100/h | $4,000.00 |
| Consulting | 10h | $150/h | $1,500.00 |
| Support Package | 1 | $500 | $500.00 |

## Approval Checklist
- [ ] Client information verified
- [ ] Services rendered confirmed
- [ ] Amounts calculated correctly
- [ ] Tax applied properly
- [ ] Payment terms correct
- [ ] Client notified of invoice

## Action Required
**Move this file to `/Approved/` to confirm posting in Odoo**

---
*Generated on 2024-01-21 by Claude*
*Original request: Needs_Action/invoice-clientA-2024-01-21.md*
```

## Commands Reference

### Invoice Processing
```bash
# Process single file
/odoo-invoice-process --file "Needs_Action/invoice-clientA-2024-01-21.md"

# Process all pending
/odoo-invoice-process-all

# Process with custom date
/odoo-invoice-process --file "Needs_Action/invoice-clientA.md" --date 2024-01-21
```

### Approval Management
```bash
# Check approval status
/odoo-invoice-approval-check --client "Client A" --date 2024-01-21

# List pending approvals
/odoo-invoice-pending-list

# Post approved invoice
/odoo-invoice-post --approval-file "/Approved/INVOICE_ClientA_2024-01-21.md"

# Batch post approved invoices
/odoo-invoice-post-all-approved
```

### Status & Reporting
```bash
# Get invoice status
/odoo-invoice-status INV/2026/0001

# List invoices by status
/odoo-invoice-list --status draft

# Generate daily report
/odoo-invoice-report --date 2024-01-21
```

## Data Processing Logic

### Invoice Creation Function
```python
def create_odoo_invoice(client_name, invoice_data):
    # 1. Read client file
    client = read_client_file(client_name)

    # 2. Validate client exists in Odoo
    partner_id = get_odoo_partner(client['odoo_partner_id'])

    # 3. Parse invoice lines
    lines = parse_invoice_lines(invoice_data['services'])

    # 4. Calculate totals
    subtotal = sum(line['amount'] for line in lines)
    tax = calculate_tax(subtotal, client['tax_rate'])
    total = subtotal + tax

    # 5. Create draft invoice
    draft_id = odoo_create_draft({
        'partner_id': partner_id,
        'move_type': 'out_invoice',
        'invoice_date': invoice_data['date'],
        'invoice_line_ids': lines,
        'state': 'draft'
    })

    # 6. Generate approval file
    create_approval_file({
        'client': client_name,
        'amount': total,
        'odoo_draft_id': draft_id,
        'invoice_number': generate_invoice_number()
    })

    return draft_id
```

### Approval Detection
```python
def check_approved_invoices():
    approved_path = "/Approved/"
    for file in os.listdir(approved_path):
        if file.startswith("INVOICE_") and file.endswith(".md"):
            approval_data = read_approval_file(f"{approved_path}{file}")
            if approval_data['status'] == 'pending':
                post_invoice_to_odoo(approval_data)
                move_to_done(file)
```

## Log Management

### Log Entry Format
**Location:** `/Logs/YYYY-MM-DD.json`

```json
{
  "timestamp": "2024-01-21T14:30:00Z",
  "operation": "invoice_created",
  "client": "Client A",
  "invoice_number": "INV/2026/0001",
  "amount": 6000.00,
  "odoo_draft_id": 567,
  "status": "pending_approval",
  "files": {
    "original": "Needs_Action/invoice-clientA-2024-01-21.md",
    "approval": "Pending_Approval/INVOICE_ClientA_2024-01-21.md"
  },
  "operator": "claude"
}
```

### Log Categories
- `invoice_created` - Draft invoice created in Odoo
- `approval_generated` - Approval file created
- `invoice_approved` - Invoice approved by human
- `invoice_posted` - Invoice posted in Odoo
- `file_moved` - File moved between directories
- `error` - Any errors encountered

## Error Handling

### Validation Errors
```python
# Client validation
if not client_file_exists(client):
    raise ValueError(f"Client file not found: {client}")

# Odoo validation
if not odoo_partner_exists(client['odoo_partner_id']):
    raise ValueError(f"Partner not found in Odoo: {client['odoo_partner_id']}")

# Amount validation
if total_amount > 10000 and not is_high_value_approved(total):
    raise ValueError("High-value invoice requires additional approval")
```

### Recovery Procedures
1. **Failed Odoo creation**: Retry with exponential backoff
2. **Missing approval files**: Regenerate from logs
3. **Partial uploads**: Verify and resume
4. **File permission errors**: Check directory permissions

## Security & Compliance

### HITL Enforcement
```python
def post_invoice_to_odoo(approval_data):
    # MANDATORY: Check approval file exists
    if not file_exists_in_approved(approval_data['file']):
        raise SecurityError("Invoice not approved - missing approval file")

    # MANDATORY: Verify approval status
    if not is_truly_approved(approval_data):
        raise SecurityError("Invoice approval verification failed")

    # MANDATORY: Check amount thresholds
    if approval_data['amount'] > 100:
        log_high_value_transaction(approval_data)

    # Proceed with posting
    return odoo_post_invoice(approval_data['odoo_draft_id'])
```

### Audit Trail
- All operations logged with timestamps
- File movements tracked
- User actions recorded
- Approval chain documented

## Integration Points

### With odoo-integration Skill
```python
# Use odoo-integration for connectivity
odoo_skill = get_skill('odoo-integration')
session = odoo_skill.authenticate()
draft_id = odoo_skill.create_draft(invoice_data)
```

### With invoice-generator Skill
```python
# Can trigger invoice-generator for pre-processing
if needs_invoice_generation(client_data):
    invoice_skill = get_skill('invoice-generator')
    invoice_data = invoice_skill.generate_invoice(client_data)
```

## File System Operations

### Directory Monitoring
```python
def monitor_needs_action():
    """Continuously monitor Needs_Action directory"""
    for file in watch_directory("/Needs_Action/"):
        if file.startswith("invoice-"):
            process_invoice_file(file)
```

### File Movement Rules
```python
def move_invoice_file(source, destination, status):
    """Move file and update logs"""
    shutil.move(source, destination)
    log_file_movement(source, destination, status)
    update_invoice_status(extract_invoice_info(source), status)
```

## Performance Optimization

### Batch Processing
```python
def batch_process_invoices():
    """Process multiple invoices efficiently"""
    pending_files = get_pending_invoice_files()

    # Group by client for efficiency
    client_groups = group_by_client(pending_files)

    for client, files in client_groups.items():
        with odoo_transaction():
            for file in files:
                process_single_invoice(file)
```

### Caching
- Cache client information
- Cache Odoo partner IDs
- Cache rate information
- Cache journal details

## Troubleshooting

### Common Issues
1. **"Client not found in Odoo"**
   - Verify client file has correct odoo_partner_id
   - Check client exists in Odoo
   - Update client file if needed

2. **"Approval file not found"**
   - Check file was created in /Pending_Approval/
   - Verify file naming convention
   - Check file permissions

3. **"Invoice already exists"**
   - Check for duplicate in Needs_Action
   - Verify invoice numbering
   - Check Odoo for existing invoice

4. **"Permission denied"**
   - Verify directory permissions
   - Check file ownership
   - Validate .env credentials

## Best Practices

1. **Always validate before creating**
2. **Never post without explicit approval**
3. **Maintain detailed logs**
4. **Backup before bulk operations**
5. **Test with small amounts first**
6. **Regular reconciliation with Odoo**
7. **Monitor for failed operations**

## Compliance Notes

- Follow accounting standards
- Maintain audit trails
- Secure sensitive data
- Comply with tax regulations
- Document all exceptions
- Regular compliance reviews