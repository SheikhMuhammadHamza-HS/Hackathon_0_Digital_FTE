import subprocess
import sys
import time

def run_cloud_node():
    print("🌍 Starting Platinum Tier Cloud Node...")
    
    # 1. Start the Vault Synchronizer
    print("🔄 Starting Vault Sync Daemon...")
    sync_process = subprocess.Popen([sys.executable, "scripts/sync_vault.py"])
    
    # 2. Skip Gmail Watcher on Cloud (let local PC be the authority to avoid duplicates)
    print("ℹ️ Skipping Gmail Watcher on Cloud (Authority: Local PC)...")
    # watcher_process = subprocess.Popen([sys.executable, "scripts/start_unified_watcher.py"])
    
    # 3. Start the Health Monitor
    print("🏥 Starting Health Monitor...")
    health_process = subprocess.Popen([sys.executable, "scripts/start_health_monitor.py"])
    
    # Give it a moment to do an initial sync
    time.sleep(5)
    
    try:
        # Keep essential services running
        sync_process.wait()
        health_process.wait()
    except KeyboardInterrupt:
        print("\n🛑 Terminating Cloud Node...")
        sync_process.terminate()
        health_process.terminate()
    

if __name__ == "__main__":
    run_cloud_node()
