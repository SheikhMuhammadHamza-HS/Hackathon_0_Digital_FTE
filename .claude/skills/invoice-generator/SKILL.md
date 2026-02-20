---
name: invoice-generator
description: Generate professional invoices by reading client details, calculating totals, handling taxes, and creating approval workflows. Use when Claude needs to: (1) Create new invoices for clients, (2) Calculate invoice totals with tax, (3) Manage invoice status tracking, (4) Generate invoice numbers automatically, (5) Create pending approval files for review
license: Complete terms in LICENSE.txt
---

# Invoice Generator

This skill automates the creation of professional invoices with proper calculations, tax handling, and approval workflows.

## Quick Start

Generate an invoice for a client:
```bash
/invoice-generator <client-name> <period> <items>
```

Example:
```bash
/invoice-generator Acme-Corp "2024-01" "Web Development:40h, Consulting:10h"
```

## Core Workflow

### 1. Read Required Data

**Client Details:**
- Read from: `/Vault/Clients/<client-name>.md`
- Extract: Name, address, contact info, tax ID, payment terms

**Rates and Pricing:**
- Read from: `/Vault/Accounting/Rates.md`
- Extract: Hourly rates, service rates, tax percentages

### 2. Generate Invoice

**Create invoice file:** `/Vault/Invoices/INV-<YYYY>-<NNNN>.md`

Invoice format:
```markdown
---
invoice_number: INV-2024-0001
date: 2024-01-15
due_date: 2024-02-15
status: draft
client: <client-name>
subtotal: 1500.00
tax: 150.00
total: 1650.00
---

# Invoice INV-2024-0001

**Date:** 2024-01-15
**Due Date:** 2024-02-15
**Status:** Draft

## Bill To:
[Client details from client file]

## Items:
| Description | Quantity | Rate | Amount |
|-------------|----------|------|--------|
| Web Development | 40h | $50/h | $2000.00 |
| Consulting | 10h | $75/h | $750.00 |

## Summary:
- Subtotal: $2750.00
- Tax (10%): $275.00
- **Total: $3025.00**
```

### 3. Create Approval Request

**Create pending approval file:** `/Vault/Pending_Approval/Invoice-INV-<YYYY>-<NNNN>-<client-name>.md`

Content includes:
- Invoice summary
- Total amount
- Client details
- Approval checklist

### 4. Log Creation

**Log entry in:** `/Vault/Logs/invoice-creation-<YYYY-MM>.md`

Log format:
```markdown
## 2024-01-15 10:30 - Invoice Created
- Invoice: INV-2024-0001
- Client: Acme Corp
- Total: $3025.00
- Status: Pending Approval
- Created by: Claude
```

## Implementation Details

### Invoice Number Generation

1. Read existing invoices from `/Vault/Invoices/`
2. Find highest number for current year
3. Increment by 1
4. Format: `INV-YYYY-NNNN` (zero-padded to 4 digits)

### Date Formatting

- **Issue Date:** Current date (YYYY-MM-DD)
- **Due Date:** Issue date + payment terms (default 30 days)
- Format: ISO 8601 (YYYY-MM-DD)

### Tax Calculation

1. Determine tax rate from client location or default rate
2. Calculate tax on subtotal
3. Format to 2 decimal places

### Status Tracking

Valid statuses:
- `draft` - Initial creation
- `approved` - Human approved
- `sent` - Sent to client
- `paid` - Payment received
- `overdue` - Past due date
- `cancelled` - Cancelled

Update status by editing the invoice frontmatter.

## File Structure Assumptions

### Client File Format (`/Vault/Clients/<client-name>.md`)
```markdown
---
name: Acme Corp
address: 123 Main St, City, State 12345
contact: John Doe (john@acme.com)
tax_id: 12-3456789
payment_terms: 30
tax_rate: 10
---
```

### Rates File Format (`/Vault/Accounting/Rates.md`)
```markdown
# Standard Rates

## Services
- Web Development: $50/hour
- Consulting: $75/hour
- Design: $60/hour

## Products
- Software License: $500
- Support Package: $200/month
```

## Error Handling

- If client file doesn't exist: Ask for client details
- If rates file doesn't exist: Use default rates or ask
- If invoice number conflict: Increment to next available
- If tax calculation fails: Use 0% tax and note in invoice

## Commands Reference

### Generate Invoice
```bash
invoice-generator <client> <period> <items>
```

### Update Status
```bash
invoice-update <invoice-number> <new-status>
```

### List Invoices
```bash
invoice-list [client] [status]
```

## Best Practices

1. Always verify calculations before creating approval request
2. Check for duplicate invoices before generation
3. Use consistent date formatting
4. Include all relevant details in approval requests
5. Log all invoice activities for audit trail
6. Backup invoice files regularly

## Troubleshooting

**Common Issues:**
- Missing client files: Create client template first
- Incorrect totals: Verify rates and quantities
- Tax errors: Check client tax settings
- Approval delays: Ensure approval files are properly created