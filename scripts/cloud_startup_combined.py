import subprocess
import sys
import time
import os

def run_combined_node():
    print("🌍 Starting AI Employee (Combined Web & Background Services)...")
    
    # 1. Start the Background Scripts
    print("🔄 Starting Vault Sync Daemon...")
    sync_process = subprocess.Popen([sys.executable, "scripts/sync_vault.py"])
    
    print("📧 Starting Unified Watcher (Gmail)...")
    watcher_process = subprocess.Popen([sys.executable, "scripts/start_unified_watcher.py"])
    
    print("🏥 Starting Health Monitor...")
    health_process = subprocess.Popen([sys.executable, "scripts/start_health_monitor.py"])
    
    # 2. Start the FastAPI Web Server (Gunicorn)
    print("🚀 Starting FastAPI Web Server...")
    port = os.environ.get("PORT", "10000")
    # Hum gunicorn ko aik process ke taur pe chalayen ge aur iska wait karenge (taake Render band na ho jaye)
    web_command = [
        "gunicorn",
        "ai_employee.api.server:app",
        "--workers", "2",
        "--worker-class", "uvicorn.workers.UvicornWorker",
        "--bind", f"0.0.0.0:{port}"
    ]
    
    web_process = subprocess.Popen(web_command)
    
    try:
        # Keep everything running
        # Agar Web Server crash ho toh hum use detect kar saktay hain
        web_process.wait()
    except KeyboardInterrupt:
        print("\n🛑 Terminating Integrated Node...")
        sync_process.terminate()
        watcher_process.terminate()
        health_process.terminate()
        web_process.terminate()

if __name__ == "__main__":
    run_combined_node()
