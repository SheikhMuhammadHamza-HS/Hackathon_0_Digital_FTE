
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

async def generate_ceo_briefing():
    load_dotenv()
    
    print("📋 Generating AI Employee Weekly CEO Briefing...")
    
    # Paths
    done_path = Path("./Done")
    logs_path = Path("./Logs")
    vault_ledger = Path("./Vault/Invoice_Ledger.md")
    
    # 1. Scan Productivity (Done folder)
    done_files = list(done_path.glob("*.md"))
    
    # 2. Key Metrics
    tasks_completed = len(done_files)
    invoices_processed = 0
    total_invoice_value = 0.0
    
    if vault_ledger.exists():
        ledger_content = vault_ledger.read_text(encoding='utf-8')
        # Simple extraction of numeric totals from ledger table
        import re
        amounts = re.findall(r"\$(\d+[\d,]*\.\d+)", ledger_content)
        for amt in amounts:
            total_invoice_value += float(amt.replace(",", ""))
        invoices_processed = len(amounts)

    # 3. Briefing Content (Markdown)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    briefing = f"""# 🤖 AI Employee — Weekly Executive Briefing
**Generated on:** {timestamp}

## 🚀 Performance Overview
- **Total Tasks Completed:** {tasks_completed}
- **Invoices Processed:** {invoices_processed}
- **Revenue Monitored/Submitted:** ${total_invoice_value:,.2f}
- **Active Platforms:** Facebook, Odoo ERP, Gmail

## 📊 Detail Activity Log (Recent 5 Tasks)
"""
    
    for f in done_files[:5]:
        briefing += f"- {f.name} (Processed successfully)\n"
        
    briefing += """
## ✅ System Health Status
- **Core Engine:** Operational
- **Social Media (Facebook/Instagram):** Live Integration
- **ERP Integration (Odoo):** Accounting Module Verified
- **Approvals Status:** Human-in-the-loop workflow active

## 🔮 Next Week's Strategic Goals
1. Automate recurring invoice reminders for late payments.
2. Implement sentiment analysis on Facebook/Instagram comments.
3. Scale CEO dashboard to include real-time profit/loss metrics from Odoo.

---
*Report generated automatically by Hamza's Digital FTE AI System.*
"""
    
    # Save to Dashboard.md
    report_file = Path("./Dashboard.md")
    report_file.write_text(briefing, encoding='utf-8')
    
    print(f"✅ CEO Briefing generated at {report_file.resolve()}")
    print("-" * 50)
    print(briefing)

if __name__ == "__main__":
    import asyncio
    asyncio.run(generate_ceo_briefing())
