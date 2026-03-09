
import os
import shutil
from pathlib import Path

def setup_modular_vault():
    root = Path("d:/hackathon_zero")
    vault = root / "Vault"
    
    # Define New Modular Structure
    folders = [
        vault / "Gmail/Inbox",
        vault / "Gmail/Sent",
        vault / "WhatsApp/Messages",
        vault / "Facebook/Posts",
        vault / "Odoo/Invoices",
        vault / "Odoo/Triggers",
        vault / "Workflow/Needs_Action",
        vault / "Workflow/Approved",
        vault / "Workflow/Done",
        vault / "Workflow/Rejected",
        vault / "Workflow/Logs"
    ]

    print("📁 Creating Modular Vault Structure...")
    for folder in folders:
        folder.mkdir(parents=True, exist_ok=True)
        print(f"  ✅ Created: {folder}")

    # Move Root Workflow Folders to Vault/Workflow
    workflow_map = {
        "Needs_Action": vault / "Workflow/Needs_Action",
        "Approved": vault / "Workflow/Approved",
        "Done": vault / "Workflow/Done",
        "Rejected": vault / "Workflow/Rejected",
        "Pending_Approval": vault / "Workflow/Pending_Approval",
        "Logs": vault / "Workflow/Logs"
    }

    print("\n📦 Moving Activity Files to Modular Folders...")
    for old_name, new_path in workflow_map.items():
        old_path = root / old_name
        if old_path.exists() and old_path.is_dir():
            print(f"  Moving {old_name} content to {new_path}")
            for item in old_path.iterdir():
                try:
                    dest = new_path / item.name
                    if dest.exists():
                        # Add timestamp if exists
                        import time
                        ts = int(time.time())
                        dest = new_path / f"{item.stem}_{ts}{item.suffix}"
                    shutil.move(str(item), str(dest))
                except Exception as e:
                    print(f"    ⚠️ Could not move {item.name}: {e}")
            # Try to remove old empty dir (optional)
            try:
                os.rmdir(old_path)
            except:
                pass

    print("\n✨ Cleaning up redundant root files...")
    obsolete_files = [
        root / "startup_traceback.txt",
        root / "startup_traceback_utf8.txt",
        root / "watcher_output.txt",
        root / "test_output.ignore"
    ]
    for obs in obsolete_files:
        if obs.exists():
            obs.unlink()
            print(f"  🗑️ Deleted redundant: {obs.name}")

    print("\n✅ Organization Complete!")

if __name__ == "__main__":
    setup_modular_vault()
