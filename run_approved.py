"""
Run Approved Items — processes all files in /Approved folder.
This is Step 2 of the HITL flow: Human approved → Execute → Done
"""
import os
import sys
import asyncio
from pathlib import Path
from datetime import datetime

# Set UTF-8 output
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Change to project root
os.chdir(Path(__file__).parent)

# Load env
from dotenv import load_dotenv
load_dotenv()

# Override paths
os.environ.setdefault("NEEDS_ACTION_PATH", "./Vault/Workflow/Needs_Action")
os.environ.setdefault("PENDING_APPROVAL_PATH", "./Vault/Workflow/Pending_Approval")
os.environ.setdefault("APPROVED_PATH", "./Vault/Workflow/Approved")
os.environ.setdefault("DONE_PATH", "./Vault/Workflow/Done")

APPROVED_DIR = Path("./Vault/Workflow/Approved")
DONE_DIR = Path("./Vault/Workflow/Done")

DONE_DIR.mkdir(exist_ok=True)

print("=" * 65)
print("  RALPH WIGGUM — APPROVED ITEMS EXECUTOR")
print("  Step 2: Human Approved → Execute → Done")
print("=" * 65)
print(f"  Approved folder : {APPROVED_DIR.resolve()}")
print(f"  Done folder     : {DONE_DIR.resolve()}")
print("=" * 65)

PLATINUM_MODE = os.getenv("PLATINUM_MODE", "local").lower()
if PLATINUM_MODE == "cloud":
    print("\n☁️ [PLATINUM] Running in CLOUD mode.")
    print("   Execution of Approved items is RESTRICTED to the Local Node.")
    print("   Please run this script on your Local machine to process approvals.")
    sys.exit(0)
    

approved_files = list(APPROVED_DIR.glob("*.md"))

if not approved_files:
    print("\n[INFO] No approved files found. Nothing to process.")
    sys.exit(0)

print(f"\n[INFO] Found {len(approved_files)} approved file(s):\n")
for f in approved_files:
    print(f"  -> {f.name}")

print("\n" + "-" * 65)

# Process each approved file
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from src.services.action_executor import ActionExecutor
    executor = ActionExecutor()
except Exception as e:
    print(f"[ERROR] Could not initialize ActionExecutor: {e}")
    # Fallback: just log and move
    executor = None

results = []

for approved_file in approved_files:
    print(f"\n[PROCESSING] {approved_file.name}")
    print(f"  Platform: checking...")

    # Read platform header
    try:
        content = approved_file.read_text(encoding='utf-8')
        platform = "unknown"
        subject = ""
        for line in content.splitlines()[:5]:
            if line.lower().startswith("platform:"):
                platform = line.split(":", 1)[1].strip()
            if line.lower().startswith("subject:"):
                subject = line.split(":", 1)[1].strip()
        print(f"  Platform: {platform}")
        print(f"  Subject : {subject}")
    except Exception as e:
        print(f"  [WARN] Could not read file: {e}")
        content = ""
        platform = "unknown"
        subject = approved_file.name

    # Execute action
    success = False
    if executor:
        try:
            print(f"  [ACTION] Executing via ActionExecutor...")
            success = executor.execute(approved_file)
        except Exception as e:
            print(f"  [ERROR] ActionExecutor failed: {e}")
            success = False

        # EXECUTION DISPATCHER
        if platform == "email" or "gmail" in approved_file.name.lower():
            print(f"  [GMAIL]   Detected Email Task — Attempting to send...")
            try:
                from src.agents.email_sender import EmailSender
                sender = EmailSender()
                success = sender.send_draft(approved_file)
                if success:
                    print(f"  ✅ SUCCESS: Email sent to recipient!")
                else:
                    print(f"  ❌ FAILED: Could not send email via Gmail API.")
            except Exception as e:
                print(f"  ❌ ERROR: EmailSender failed: {e}")
                success = False

        elif platform == "file_action" or "invoice" in approved_file.name.lower():
            print(f"  [ODOO]    Detected Invoice Task — Recording action...")

            # Write to Vault ledger manually
            import re
            total_due = 0.0
            client_name = "Unknown Client"
            invoice_number = "N/A"
            due_date = "N/A"

            for line in content.splitlines():
                ll = line.lower()
                # Generic client name extraction
                if "client:" in ll:
                    parts = line.split(":", 1)
                    if len(parts) > 1:
                        client_name = parts[1].strip()
                if "total due" in ll:
                    amounts = re.findall(r"\$[\d,]+\.?\d*", line)
                    if amounts:
                        total_due = float(amounts[-1].replace("$","").replace(",",""))
                if "inv-" in ll:
                    m = re.search(r"INV[-\w]+", line, re.I)
                    if m:
                        invoice_number = m.group(0)
                if "due date" in ll:
                    m = re.search(r"\d{4}-\d{2}-\d{2}|[A-Z][a-z]+ \d+, \d{4}", line)
                    if m:
                        due_date = m.group(0)

            # Write Odoo trigger
            vault_na = Path("./Vault/Odoo/Triggers")
            vault_na.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime('%Y%m%dT%H%M%SZ')
            trigger_path = vault_na / f"odoo-invoice-{ts}.md"
            trigger_path.write_text(f"""# Odoo Invoice Submission — APPROVED

**Action:** CREATE_INVOICE
**Status:** APPROVED_BY_HUMAN
**Source:** {approved_file.name}
**Timestamp:** {datetime.now().isoformat()}

## Invoice Details
- **Client:** {client_name}
- **Invoice Number:** {invoice_number}
- **Total Due:** ${total_due:,.2f}
- **Due Date:** {due_date}

## Original Content
{content}
""", encoding='utf-8')
            print(f"  [ODOO]    Trigger file created: {trigger_path.name}")

            # Append to ledger
            ledger = Path("./Vault/Invoice_Ledger.md")
            with open(ledger, "a", encoding="utf-8") as lf:
                lf.write(
                    f"\n| {datetime.now().strftime('%Y-%m-%d %H:%M')} "
                    f"| {client_name} | {invoice_number} | ${total_due:,.2f} "
                    f"| {due_date} | SUBMITTED_TO_ODOO | {approved_file.name} |"
                )
            print(f"  [LEDGER]  Invoice recorded in Vault/Invoice_Ledger.md")
            success = True

    # Move to Done
    if success:
        done_path = DONE_DIR / approved_file.name
        if done_path.exists():
            ts = datetime.now().strftime("%H%M%S")
            done_path = DONE_DIR / f"{approved_file.stem}_{ts}{approved_file.suffix}"
        approved_file.rename(done_path)
        print(f"  [DONE]    Moved to Done/ -> {done_path.name}")
        results.append(("SUCCESS", approved_file.name))
    else:
        print(f"  [FAILED]  Could not process {approved_file.name}")
        results.append(("FAILED", approved_file.name))

# Summary
print("\n" + "=" * 65)
print("  EXECUTION SUMMARY")
print("=" * 65)
for status, name in results:
    icon = "[OK]" if status == "SUCCESS" else "[XX]"
    print(f"  {icon}  {status:8s}  {name}")

print(f"\n  Total: {len(results)} file(s) processed")
print(f"  Done/ folder: {DONE_DIR.resolve()}")

if Path("./Vault/Invoice_Ledger.md").exists():
    print(f"\n  Invoice Ledger: {Path('./Vault/Invoice_Ledger.md').resolve()}")

print("\n  Next Step: Odoo trigger files are in Vault/Odoo/Triggers/")
print("  The odoo-accounting-mcp skill or Unified Watcher will post them to Odoo.")
print("=" * 65)
