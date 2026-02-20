---
name: odoo-reconciliation
description: Log payments and reconcile accounts in Odoo with transaction monitoring, invoice matching, and strict approval workflows. Depends on odoo-accounting-mcp skill. Use when Claude needs to: (1) Monitor bank transactions, (2) Match payments to Odoo invoices, (3) Create draft payments for approval, (4) Update payment dashboards, (5) Handle banking API errors and recovery
license: Complete terms in LICENSE.txt
---

# Odoo Reconciliation

This skill manages payment logging, transaction monitoring, and account reconciliation in Odoo with strict HITL approval requirements and robust error recovery.

## Dependencies

This skill requires:
- `odoo-accounting-mcp` skill for invoice integration
- `odoo-integration` skill for Odoo connectivity
- Bank_Transactions.md file monitoring
- Dashboard.md for status updates

## Quick Start

Monitor bank transactions:
```bash
/odoo-reconcile-monitor
```

Process specific transaction:
```bash
/odoo-reconcile-transaction --id TXN-001 --amount 1500 --invoice INV-2024-001
```

Check approval status:
```bash
/odoo-reconcile-status --transaction TXN-001
```

## Core Workflow

### 1. Transaction Monitoring

**Bank Transactions File (`Bank_Transactions.md`):**
```markdown
---
last_updated: 2024-01-21T14:30:00Z
processed_count: 15
---

# Bank Transactions

## Unprocessed
- **TXN-001** | 2024-01-21 | $1,500.00 | Client A | INV-2024-001
- **TXN-002** | 2024-01-21 | $45.00 | Client B | recurring

## Processed
- ~~TXN-000~~ | 2024-01-20 | $2,000.00 | Client C | INV-2024-000
```

**Monitoring Process:**
1. Watch for new entries in Bank_Transactions.md
2. Parse transaction details
3. Match against open invoices in Odoo
4. Determine approval requirements
5. Create draft payments

### 2. Invoice Matching Logic

**Matching Algorithm:**
```python
def match_transaction_to_invoice(transaction):
    # 1. Exact invoice match
    if transaction.invoice_reference:
        invoice = find_invoice(transaction.invoice_reference)
        if invoice and invoice.amount == transaction.amount:
            return {'match': 'exact', 'invoice': invoice}

    # 2. Amount-based match
    open_invoices = get_open_invoices_for_client(transaction.client)
    for invoice in open_invoices:
        if abs(invoice.amount - transaction.amount) < 0.01:
            return {'match': 'amount', 'invoice': invoice}

    # 3. Partial match
    for invoice in open_invoices:
        if transaction.amount < invoice.amount:
            return {'match': 'partial', 'invoice': invoice}

    return {'match': 'none', 'invoice': None}
```

### 3. Approval Management

**HITL Rules (Strict Enforcement):**

| Condition | Approval Required | Action |
|-----------|-------------------|--------|
| New payee | **ALWAYS** | Create approval file |
| Payment > $100 | **ALWAYS** | Create approval file |
| Recurring < $50 | No | Auto-log only |
| Banking API timeout | **ALWAYS** | Fresh approval needed |
| First-time client | **ALWAYS** | Enhanced verification |

**Approval File Structure:**
```markdown
---
type: payment_approval
transaction_id: TXN-001
client: Client A
amount: 1500.00
invoice_id: INV-2024-001
odoo_payment_id: draft-789
match_type: exact
status: pending
risk_level: medium
date: 2024-01-21
---

# Payment Approval Request

## Transaction Details
- **Transaction ID:** TXN-001
- **Date:** 2024-01-21
- **Amount:** $1,500.00
- **Client:** Client A (NEW PAYEE ✋)
- **Invoice:** INV-2024-001
- **Match Type:** Exact

## Approval Required Because
- [ ] New payee (first time payment)
- [x] Amount exceeds $100 threshold
- [ ] Partial payment match
- [ ] Manual review needed

## Verification Checklist
- [ ] Invoice exists and is open
- [ ] Amount matches invoice
- [ ] Client information verified
- [ ] Banking transaction confirmed
- [ ] No duplicate payments detected

## Action Required
**Move to `/Approved/` to process payment in Odoo**

⚠️ **This payment requires manual approval**
---
*Generated: 2024-01-21 14:30*
```

### 4. Dashboard Updates

**Dashboard.md Integration:**
```markdown
## Payment Status - 2024-01-21

### Pending Approval
- TXN-001 | Client A | $1,500.00 | [Review](Pending_Approval/PAYMENT_TXN-001.md)
- TXN-002 | Client B | $45.00 | [Auto-logged]

### Processed Today
- ✅ TXN-000 | Client C | $2,000.00 | Posted to Odoo
- ✅ TXN-999 | Client D | $25.00 | Auto-reconciled

### Summary
- Total Received: $3,570.00
- Pending Approval: $1,545.00
- Processed: $2,025.00
- Conversion Rate: 56.7%
```

## Implementation Details

### Payment Creation Function
```python
def create_odoo_payment(transaction, invoice_match):
    payment_data = {
        'payment_type': 'inbound',
        'partner_type': 'customer',
        'partner_id': invoice_match['invoice'].partner_id,
        'amount': transaction.amount,
        'journal_id': get_bank_journal(),
        'payment_method_id': get_payment_method('manual'),
        'invoice_ids': [(6, 0, [invoice_match['invoice'].id])],
        'state': 'draft'
    }

    # Create draft payment
    draft_id = odoo_create_draft('account.payment', payment_data)

    # Determine if approval needed
    if requires_approval(transaction, invoice_match):
        create_payment_approval(transaction, invoice_match, draft_id)
    else:
        # Auto-log but don't post
        auto_log_payment(transaction, draft_id)

    return draft_id
```

### Approval Requirements Logic
```python
def requires_approval(transaction, invoice_match):
    # Rule 1: New payee always requires approval
    if is_new_payee(transaction.client):
        return True, "New payee requires verification"

    # Rule 2: Payments > $100 always require approval
    if transaction.amount > 100:
        return True, f"Amount ${transaction.amount} exceeds $100 threshold"

    # Rule 3: Recurring < $50 can auto-log
    if transaction.amount < 50 and transaction.is_recurring:
        return False, "Recurring payment under $50"

    # Rule 4: Partial matches require review
    if invoice_match['match_type'] == 'partial':
        return True, "Partial payment match requires review"

    # Rule 5: No match requires review
    if invoice_match['match_type'] == 'none':
        return True, "No invoice match found"

    return False, "Standard processing"
```

### Error Recovery Mechanisms

**Banking API Down:**
```python
def handle_banking_api_down():
    """Queue transactions locally when API is down"""
    queue_file = "/Vault/Queued/transactions-queue.json"

    # Move unprocessed to queue
    for transaction in get_unprocessed_transactions():
        queue_transaction({
            'transaction': transaction,
            'timestamp': datetime.now().isoformat(),
            'status': 'queued',
            'retry_count': 0
        })

    # Mark in Bank_Transactions.md
    update_transaction_status(transaction.id, 'queued')

    log_event('banking_api_down', {
        'queued_count': len(queued_transactions),
        'next_retry': calculate_next_retry()
    })
```

**Never Auto-Retry Policy:**
```python
def process_payment(payment_data):
    try:
        # Attempt processing
        result = odoo_post_payment(payment_data)
        return result
    except BankingAPIError:
        # NEVER retry automatically
        log_error('banking_api_failed', payment_data)
        create_manual_approval(payment_data, "Banking API error - manual review required")
        raise BankingAPIError("Payment processing failed - manual approval required")
    except Exception as e:
        # Other errors also require approval
        log_error('payment_processing_failed', {'error': str(e), 'data': payment_data})
        create_manual_approval(payment_data, f"Processing error: {str(e)}")
        raise
```

## Commands Reference

### Monitoring Commands
```bash
# Monitor bank transactions
/odoo-reconcile-monitor

# Monitor with interval
/odoo-reconcile-monitor --interval 300

# Check specific transaction
/odoo-reconcile-check --transaction TXN-001

# List all pending
/odoo-reconcile-pending
```

### Processing Commands
```bash
# Process single transaction
/odoo-reconcile-process --transaction TXN-001

# Process all unprocessed
/odoo-reconcile-process-all

# Force reprocess
/odoo-reconcile-reprocess --transaction TXN-001 --force
```

### Approval Commands
```bash
# Check approval status
/odoo-reconcile-approval-status --transaction TXN-001

# List pending approvals
/odoo-reconcile-approvals-pending

# Process approved payments
/odoo-reconcile-process-approved

# Manual approval override
/odoo-reconcile-approve --transaction TXN-001 --reason "Verified manually"
```

### Recovery Commands
```bash
# Check queue status
/odoo-reconcile-queue-status

# Process queued items
/odoo-reconcile-process-queue

# Recovery from API failure
/odoo-reconcile-recover --date 2024-01-21

# Reconcile mismatches
/odoo-reconcile-mismatches
```

## Log Management

### Log Entry Format
**Location:** `/Logs/YYYY-MM-DD.json`

```json
{
  "timestamp": "2024-01-21T14:30:00Z",
  "operation": "payment_processed",
  "transaction_id": "TXN-001",
  "client": "Client A",
  "amount": 1500.00,
  "invoice_id": "INV-2024-001",
  "odoo_payment_id": "draft-789",
  "approval_required": true,
  "approval_file": "Pending_Approval/PAYMENT_TXN-001.md",
  "match_type": "exact",
  "risk_level": "medium",
  "operator": "claude"
}
```

### Log Categories
- `transaction_detected` - New transaction found
- `payment_processed` - Payment created in Odoo
- `payment_approved` - Payment approved and posted
- `payment_logged` - Auto-logged without posting
- `banking_api_down` - API unavailable
- `transaction_queued` - Queued for later processing
- `mismatch_detected` - No invoice match found
- `duplicate_detected` - Duplicate payment identified

## File System Operations

### Transaction Queue Management
```python
def manage_transaction_queue():
    queue_file = "/Vault/Queued/transactions-queue.json"

    # Load queue
    queue = load_json(queue_file) or []

    # Process ready items
    for item in queue:
        if is_ready_for_retry(item):
            try:
                process_transaction(item['transaction'])
                queue.remove(item)
            except BankingAPIError:
                item['retry_count'] += 1
                item['last_retry'] = datetime.now().isoformat()

    # Save updated queue
    save_json(queue_file, queue)
```

### Dashboard Updates
```python
def update_payment_dashboard():
    dashboard_file = "Dashboard.md"

    # Gather statistics
    stats = {
        'pending_count': count_pending_approvals(),
        'pending_amount': sum_pending_amounts(),
        'processed_today': count_processed_today(),
        'total_received': calculate_total_received()
    }

    # Update dashboard
    update_dashboard_section(dashboard_file, 'Payment Status', stats)
```

## Security & Risk Management

### Risk Assessment
```python
def assess_payment_risk(transaction, invoice_match):
    risk_score = 0
    factors = []

    # New payee risk
    if is_new_payee(transaction.client):
        risk_score += 30
        factors.append("New payee")

    # High amount risk
    if transaction.amount > 1000:
        risk_score += 20
        factors.append("High value")

    # No invoice match
    if invoice_match['match_type'] == 'none':
        risk_score += 40
        factors.append("Unmatched transaction")

    # Unusual timing
    if is_unusual_timing(transaction):
        risk_score += 10
        factors.append("Unusual timing")

    return {
        'score': risk_score,
        'level': 'low' if risk_score < 20 else 'medium' if risk_score < 50 else 'high',
        'factors': factors
    }
```

### Fraud Detection
```python
def detect_fraud_indicators(transaction):
    indicators = []

    # Duplicate check
    if is_duplicate_transaction(transaction):
        indicators.append("Duplicate transaction detected")

    # Velocity check
    if exceeds_velocity_limits(transaction.client):
        indicators.append("Exceeds payment velocity")

    # Amount anomaly
    if is_amount_anomaly(transaction.client, transaction.amount):
        indicators.append("Unusual payment amount")

    return indicators
```

## Performance Optimization

### Batch Processing
```python
def batch_process_transactions(transactions):
    """Process multiple transactions efficiently"""

    # Group by client for efficiency
    client_groups = group_by_client(transactions)

    for client, client_transactions in client_groups.items():
        with odoo_transaction():
            # Load client data once
            client_info = load_client_info(client)
            open_invoices = get_open_invoices(client)

            for transaction in client_transactions:
                process_single_transaction(transaction, client_info, open_invoices)
```

### Caching Strategy
- Cache client information
- Cache open invoices
- Cache payment methods
- Cache journal details

## Troubleshooting

### Common Issues
1. **"No invoice match found"**
   - Check invoice reference format
   - Verify client name spelling
   - Review amount matching tolerance

2. **"Banking API timeout"**
   - Check API status
   - Review transaction queue
   - Process queued items manually

3. **"Duplicate payment detected"**
   - Check transaction history
   - Verify payment IDs
   - Review bank statement

4. **"Approval file not created"**
   - Check directory permissions
   - Verify file naming convention
   - Review approval logic

## Best Practices

1. **Always verify before processing**
2. **Never auto-retry failed payments**
3. **Maintain detailed audit trails**
4. **Monitor for unusual patterns**
5. **Regular reconciliation reviews**
6. **Secure sensitive banking data**
7. **Document all exceptions**

## Compliance Notes

- Follow banking regulations
- Maintain audit trails
- Secure payment data
- Comply with AML requirements
- Document all approvals
- Regular compliance reviews
- Retain records per policy