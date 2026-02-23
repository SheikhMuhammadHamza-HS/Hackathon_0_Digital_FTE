#!/usr/bin/env python3
"""
Test Approval Detection - Detect approved invoices and post to Odoo
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import json
import asyncio

def check_approved_invoices():
    """Check for approved invoices"""
    print("="*60)
    print("APPROVAL DETECTION TEST")
    print("="*60)

    approved_dir = Path("Approved")
    if not approved_dir.exists():
        print("[ERROR] /Approved directory not found")
        return []

    approved_invoices = []
    for file in approved_dir.glob("INVOICE_*.md"):
        print(f"\n[INFO] Found approved invoice: {file.name}")

        # Read approval file
        with open(file, "r") as f:
            content = f.read()

        # Extract metadata (simplified)
        metadata = {}
        for line in content.split('\n'):
            if ': ' in line and not line.startswith('---'):
                key, value = line.split(': ', 1)
                metadata[key] = value

        approved_invoices.append({
            'file': file,
            'metadata': metadata,
            'content': content
        })

        print(f"  Client: {metadata.get('client', 'Unknown')}")
        print(f"  Amount: ${metadata.get('amount', '0.00')}")
        print(f"  Status: {metadata.get('status', 'Unknown')}")

    return approved_invoices

async def post_to_odoo(approval_data):
    """Post approved invoice to Odoo"""
    print("\nPosting to Odoo...")

    metadata = approval_data['metadata']

    if os.getenv("DRY_RUN", "false").lower() == "true":
        print(f"  [DRY RUN] Would authenticate with Odoo")
        print(f"  [DRY RUN] Would post invoice {metadata.get('odoo_invoice_id')}")
        print(f"  [DRY RUN] Would update status to 'posted'")

        # Simulate success
        return {
            'success': True,
            'invoice_id': metadata.get('odoo_invoice_id'),
            'message': 'Invoice posted successfully (DRY RUN)'
        }
    else:
        # Real Odoo posting would happen here
        print(f"  [WARNING] Would post REAL invoice to Odoo!")

        # Import Odoo client
        sys.path.insert(0, str(Path(__file__).parent))
        from ai_employee.integrations.odoo_client import get_odoo_client

        try:
            client = get_odoo_client()
            await client.initialize()

            # Post the invoice
            draft_id = metadata.get('odoo_draft_id')
            if draft_id:
                success = await client.post_invoice(int(draft_id))
                await client.shutdown()

                return {
                    'success': success,
                    'invoice_id': metadata.get('odoo_invoice_id'),
                    'message': 'Invoice posted to Odoo'
                }
            else:
                return {
                    'success': False,
                    'message': 'No draft ID found'
                }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error: {str(e)}'
            }

def move_to_done(approval_file, result):
    """Move processed invoice to Done"""
    print("\nMoving to Done...")

    done_dir = Path("Done")
    done_dir.mkdir(exist_ok=True)

    # Create done file with result
    done_file = done_dir / f"invoice-{approval_file['metadata'].get('client', 'unknown').lower().replace(' ', '-')}-{datetime.now().strftime('%Y-%m-%d')}.md"

    # Add processing result to content
    content = approval_file['content']
    content += f"\n\n---\n**Processed on:** {datetime.now().isoformat()}\n"
    content += f"**Result:** {result['message']}\n"
    content += f"**Status:** {'Posted' if result['success'] else 'Failed'}\n"

    with open(done_file, "w") as f:
        f.write(content)

    print(f"  [OK] Created {done_file}")

    # Remove from Approved
    approval_file['file'].unlink()
    print(f"  [OK] Removed from Approved")

def log_operation(operation, details):
    """Log operation"""
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

async def main():
    """Main approval detection workflow"""
    # Set environment
    os.environ["DRY_RUN"] = "true"

    # Check for approved invoices
    approved_invoices = check_approved_invoices()

    if not approved_invoices:
        print("\n[INFO] No approved invoices found")
        return

    # Process each approved invoice
    for approval in approved_invoices:
        print("\n" + "="*60)
        print(f"PROCESSING: {approval['file'].name}")
        print("="*60)

        # Post to Odoo
        result = await post_to_odoo(approval)

        # Log the operation
        log_operation("invoice_posted", {
            "file": str(approval['file']),
            "client": approval['metadata'].get('client'),
            "amount": approval['metadata'].get('amount'),
            "result": result
        })

        # Move to Done
        if result['success']:
            move_to_done(approval, result)

        print(f"\nResult: {result['message']}")

    # Summary
    print("\n" + "="*60)
    print("APPROVAL PROCESSING COMPLETE")
    print("="*60)
    print(f"Processed {len(approved_invoices)} invoice(s)")

if __name__ == "__main__":
    asyncio.run(main())