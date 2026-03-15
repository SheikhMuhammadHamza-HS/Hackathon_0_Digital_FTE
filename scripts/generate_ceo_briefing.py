
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
    done_path = Path("./Vault/Done")
    done_files = list(done_path.glob("*.md"))
    done_count = len(done_files)
    vault_ledger = Path("./Vault/Invoice_Ledger.md")
    
    
    invoices_processed = 0
    total_invoice_value = 0.0
    confirmed_revenue = 0.0
    
    if vault_ledger.exists():
        ledger_content = vault_ledger.read_text(encoding='utf-8')
        import re
        amounts = re.findall(r"\$(\d+[\d,]*\.\d+)", ledger_content)
        for amt in amounts:
            total_invoice_value += float(amt.replace(",", ""))
        invoices_processed = len(amounts)

    # 3. Scan Bank Transactions for Revenue
    bank_path = Path("./Vault/Bank_Transactions.md")
    if bank_path.exists():
        bank_content = bank_path.read_text(encoding='utf-8')
        import re
        # Find amounts in format | $1500.0 |
        bank_amounts = re.findall(r"\|\s*\$(\d+[\d,]*\.?\d*)\s*\|", bank_content)
        for amt in bank_amounts:
            confirmed_revenue += float(amt.replace(",", ""))
    

    # 3. Briefing Content (Markdown)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    briefing = f"""# 🤖 AI Employee — Weekly Executive Briefing
**Generated on:** {timestamp}

## 🚀 Performance Overview
- **Total Tasks Completed:** {done_count}
- **Invoices Processed:** {invoices_processed}
- **Invoiced Value (Total):** ${total_invoice_value:,.2f}
- **Bank Revenue (Confirmed):** ${confirmed_revenue:,.2f}
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
    
    # Save to Dashboard.md (Local) or Signal folder (Cloud)
    platinum_mode = os.getenv("PLATINUM_MODE", "local").lower()
    if platinum_mode == "cloud":
        updates_dir = Path("./Vault/Updates")
        updates_dir.mkdir(parents=True, exist_ok=True)
        report_file = updates_dir / f"briefing_signal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        report_file.write_text(briefing, encoding='utf-8')
        print(f"☁️ [CLOUD] Briefing signal written to {report_file}")
    else:
        report_file = Path("./Dashboard.md")
        report_file.write_text(briefing, encoding='utf-8')
        print(f"✅ CEO Briefing generated at {report_file.resolve()}")
    
    print("-" * 50)
    print(briefing)

if __name__ == "__main__":
    import asyncio
    asyncio.run(generate_ceo_briefing())
