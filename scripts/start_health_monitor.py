import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_employee.utils.health_monitor import HealthMonitor
from src.config.logging_config import get_logger

logger = get_logger("HealthMonitorRunner")

async def run_health_monitor():
    load_dotenv()
    
    print("\n" + "="*70)
    print("🏥 AI EMPLOYEE HEALTH MONITORING SYSTEM")
    print("="*70)
    
    platinum_mode = os.getenv("PLATINUM_MODE", "local").lower()
    print(f"🌍 PLATINUM MODE: {platinum_mode.upper()}")
    
    # Initialize health monitor
    monitor = HealthMonitor()
    await monitor.initialize()
    
    print("✅ Health monitoring active. Writing status signals to Vault...")

    updates_dir = Path("./Vault/Updates")
    updates_dir.mkdir(parents=True, exist_ok=True)

    try:
        while True:
            # Gather health info
            report = await monitor.run_check("cpu_usage")
            report_mem = await monitor.run_check("memory_usage")
            
            # Simple status signal for the Dashboard UI
            status_name = report.status.name if hasattr(report.status, 'name') else str(report.status)
            cpu_val = report.metrics[0].value if report.metrics else 0
            ram_val = report_mem.metrics[0].value if report_mem.metrics else 0
            
            status_text = f"| {time.strftime('%Y-%m-%d %H:%M:%S')} | System Health: {status_name} | CPU: {cpu_val}% | RAM: {ram_val}% |"
            
            # Write signal file
            signal_file = updates_dir / "health_signal.txt"
            signal_file.write_text(status_text, encoding="utf-8")
            
            print(f"🏥 {status_text}")
            
            await asyncio.sleep(60) # Log health every minute
            
    except KeyboardInterrupt:
        print("\n🛑 Health Monitor stopped.")
        await monitor.shutdown()
    except Exception as e:
        print(f"\n❌ Health Monitor Error: {e}")
        logger.error(f"Health Monitor failed: {e}")
        await monitor.shutdown()

if __name__ == "__main__":
    import time
    asyncio.run(run_health_monitor())
