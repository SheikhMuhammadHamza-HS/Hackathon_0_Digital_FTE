#!/usr/bin/env python3
"""
Test Invoice Workflow - Simulate complete invoice process
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import json

def setup_test_environment():
    """Setup test environment with mock data"""
    print("="*60)
    print("INVOICE WORKFLOW TEST (DRY RUN)")
    print("="*60)

    # Set environment
    os.environ["DRY_RUN"] = "true"
    os.environ["ENVIRONMENT"] = "test"

    # Check if we're in dry run mode
    dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
    if dry_run:
        print("\n[INFO] Running in DRY RUN mode - No actual Odoo operations")
    else:
        print("\n[WARNING] NOT in dry run mode - Real operations will be performed!")
        response = input("Continue? (y/N): ")
        if response.lower() != 'y':
            print("Test cancelled")
            return False

    return True

def create_test_directories():
    """Create required directories"""
    print("\nCreating test directories...")

    directories = [
        "Inbox",
        "Needs_Action",
        "Done",
        "Logs",
        "Pending_Approval",
        "Approved",
        "Vault/Clients",
        "Vault/Accounting"
    ]

    for dir_path in directories:
        path = Path(dir_path)
        path.mkdir(parents=True, exist_ok=True)
        print(f"  [OK] {dir_path}")

def create_test_client():
    """Create a test client file"""
    print("\nCreating test client...")

    client_file = Path("Vault/Clients/Dummy Corp.md")
    client_content = """---
name: Dummy Corp
odoo_partner_id: 1
payment_terms: 30
tax_id: 12-3456789
default_journal: Sales
---

# Dummy Corp

**Address:** 456 Test Avenue, Test City, TC 67890
**Contact:** Jane Doe
**Email:** jane@dummycorp.com
**Phone:** 555-0456

## Billing Information
- **Payment Terms:** Net 30
- **Tax Rate:** 10%
- **Currency:** USD
"""

    with open(client_file, "w") as f:
        f.write(client_content)
    print(f"  [OK] Created {client_file}")

def create_invoice_request():
    """Create an invoice request in Needs_Action"""
    print("\nCreating invoice request...")

    today = datetime.now().strftime("%Y-%m-%d")
    due_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

    invoice_file = Path(f"Needs_Action/invoice-dummycorp-{today}.md")
    invoice_content = f"""---
client: Dummy Corp
date: {today}
period: {today[:7]}
due_date: {due_date}
priority: normal
---

# Invoice Request - Dummy Corp

## Services Rendered
- Software Development: 40 hours @ $100/hour
- Project Management: 10 hours @ $150/hour
- Hosting Services: $200

## Notes
- Project completed on schedule
- Additional hours approved by client
- Invoice to be sent by EOM
"""

    with open(invoice_file, "w") as f:
        f.write(invoice_content)
    print(f"  [OK] Created {invoice_file}")

    return invoice_file

def process_invoice_simulation(invoice_file):
    """Simulate invoice processing"""
    print("\nProcessing invoice...")

    # Read invoice file
    with open(invoice_file, "r") as f:
        content = f.read()

    # Extract details (simplified)
    lines = content.split('\n')
    client = None
    date = None

    for line in lines:
        if line.startswith("client: "):
            client = line.split(": ")[1]
        elif line.startswith("date: "):
            date = line.split(": ")[1]

    print(f"  [INFO] Client: {client}")
    print(f"  [INFO] Date: {date}")

    # Simulate Odoo operations
    if os.getenv("DRY_RUN", "false").lower() == "true":
        print("  [DRY RUN] Would connect to Odoo...")
        print("  [DRY RUN] Would create draft invoice...")
        draft_id = f"DRAFT-{datetime.now().timestamp()}"
        print(f"  [DRY RUN] Created draft ID: {draft_id}")
    else:
        print("  [WARNING] Would create actual invoice in Odoo!")
        draft_id = "REAL_INVOICE_ID"

    return draft_id

def create_approval_request(client, date, draft_id):
    """Create approval request file"""
    print("\nCreating approval request...")

    approval_file = Path(f"Pending_Approval/INVOICE_Dummy Corp_{date}.md")
    approval_content = f"""---
type: approval_request
action: post_invoice
client: Dummy Corp
amount: 5700.00
odoo_invoice_id: INV/2026/0001
odoo_draft_id: {draft_id}
status: pending
request_date: {date}
requested_by: claude
---

# Invoice Approval Request

## Invoice Details
- **Client:** Dummy Corp
- **Invoice Number:** INV/2026/0001
- **Amount:** $5,700.00
- **Date:** {date}
- **Due:** {(datetime.strptime(date, '%Y-%m-%d') + timedelta(days=30)).strftime('%Y-%m-%d')}
- **Odoo Draft ID:** {draft_id}

## Line Items
| Description | Quantity | Rate | Amount |
|-------------|----------|------|--------|
| Software Development | 40h | $100/h | $4,000.00 |
| Project Management | 10h | $150/h | $1,500.00 |
| Hosting Services | 1 | $200 | $200.00 |
| Subtotal | - | - | $5,700.00 |
| Tax (10%) | - | - | $570.00 |
| **Total** | - | - | **$6,270.00** |

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
*Generated on {date} by Claude*
*Original request: Needs_Action/invoice-dummycorp-{date}.md*
"""

    with open(approval_file, "w") as f:
        f.write(approval_content)
    print(f"  [OK] Created {approval_file}")

    return approval_file

def simulate_hitl_approval(approval_file):
    """Simulate Human-in-the-Loop approval"""
    print("\n=== HITL APPROVAL WORKFLOW ===")
    print(f"1. Approval file created: {approval_file}")
    print("2. Human review required:")
    print("   - Open the approval file")
    print("   - Verify all details")
    print("   - Check the approval checklist")
    print("   - Move file to /Approved/ when satisfied")

    # Simulate approval
    print("\n3. Simulating approval...")
    approved_file = Path("Approved") / approval_file.name

    if os.getenv("DRY_RUN", "false").lower() == "true":
        # In dry run, just show what would happen
        print(f"  [DRY RUN] Would move {approval_file} to {approved_file}")
        print(f"  [DRY_RUN] Would post invoice to Odoo")
        print(f"  [DRY RUN] Would move original to /Done/")
    else:
        # Actually move the file
        import shutil
        shutil.move(str(approval_file), str(approved_file))
        print(f"  [OK] Moved to {approved_file}")

    return approved_file

def log_operation(operation, details):
    """Log operation to daily log file"""
    log_file = Path(f"Logs/{datetime.now().strftime('%Y-%m-%d')}.json")

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "operation": operation,
        "details": details,
        "dry_run": os.getenv("DRY_RUN", "false").lower() == "true"
    }

    logs = []
    if log_file.exists():
        with open(log_file, "r") as f:
            logs = json.load(f)

    logs.append(log_entry)

    with open(log_file, "w") as f:
        json.dump(logs, f, indent=2)

    print(f"  [OK] Logged to {log_file}")

def main():
    """Main test workflow"""
    # Setup
    if not setup_test_environment():
        return False

    # Create test structure
    create_test_directories()
    create_test_client()

    # Create invoice request
    invoice_file = create_invoice_request()

    # Process invoice
    draft_id = process_invoice_simulation(invoice_file)

    # Create approval request
    approval_file = create_approval_request("Dummy Corp", datetime.now().strftime("%Y-%m-%d"), draft_id)

    # Simulate HITL approval
    approved_file = simulate_hitl_approval(approval_file)

    # Log operations
    log_operation("invoice_workflow", {
        "client": "Dummy Corp",
        "invoice_file": str(invoice_file),
        "approval_file": str(approval_file),
        "approved_file": str(approved_file),
        "draft_id": draft_id
    })

    # Summary
    print("\n" + "="*60)
    print("WORKFLOW COMPLETE")
    print("="*60)
    print("\nFiles created:")
    print(f"  1. Invoice Request: {invoice_file}")
    print(f"  2. Approval Request: {approval_file}")
    if Path(approved_file).exists():
        print(f"  3. Approved: {approved_file}")

    print("\nNext steps:")
    print("  1. Review the approval file")
    print("  2. Move to /Approved/ when ready")
    print("  3. System will auto-detect and post to Odoo")
    print("  4. Check Logs for operation history")

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)