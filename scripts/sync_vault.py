import os
import sys
import time
import subprocess
import logging
from pathlib import Path
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("VaultSync")

def run_git_command(args, cwd):
    try:
        result = subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr

def sync_vault(polling_interval=60):
    repo_root = Path(__file__).parent.parent
    
    # 1. Detect Branch (Prioritize Env Var, then Git, then Default)
    branch = os.getenv("GIT_BRANCH")
    
    if not branch:
        success, branch_output = run_git_command(["git", "branch", "--show-current"], cwd=repo_root)
        if success and branch_output.strip():
            branch = branch_output.strip()
        else:
            branch = "main" # Default to main if git fails / not a repo
            logger.warning(f"⚠️ Could not detect git branch (not a git repo?). Defaulting to '{branch}'.")
    
    # Check if this is actually a git repo
    is_git_repo = os.path.isdir(repo_root / ".git")
    
    print("\n" + "="*70)
    print("🔄 PLATINUM TIER: VAULT SYNC (Git-Based)")
    print(f"📡 Branch: {branch}")
    print(f"⏱️  Interval: Every {polling_interval} seconds")
    print("="*70)
    print("Press Ctrl+C to stop Vault Sync.\n")
    
    try:
        if not is_git_repo:
            logger.warning("🚫 Not a git repository! Vault Sync (Pull/Push) is disabled.")
            logger.info("ℹ️ To enable cloud sync, ensure .git folder is included in the deployment.")
            
            # Keep process alive to not crash cloud_startup
            while True:
                time.sleep(polling_interval * 10)
                
        while True:
            # 1. Pull latest changes from Cloud/Local
            logger.info("⬇️ Pulling latest Vault changes...")
            success, pull_out = run_git_command(["git", "pull", "--rebase", "--autostash", "origin", branch], cwd=repo_root)
            if not success:
                logger.warning(f"⚠️ Merge/Pull issue (could be offline): {pull_out}")
            
            # 2. Check if Vault has local changes
            success, status_out = run_git_command(["git", "status", "--porcelain", "Vault/"], cwd=repo_root)
            if success and status_out.strip():
                logger.info(f"⬆️ Local changes detected in Vault/. Pushing to {branch}...")
                
                # Add only the Vault directory
                run_git_command(["git", "add", "Vault/"], cwd=repo_root)
                run_git_command(["git", "commit", "-m", "sync(vault): Auto-sync Platinum Vault state"], cwd=repo_root)
                
                # Push back to remote
                push_success, push_out = run_git_command(["git", "push", "origin", branch], cwd=repo_root)
                if push_success:
                    logger.info("✅ Vault synced successfully.")
                else:
                    logger.error(f"❌ Failed to push: {push_out}")
            
            time.sleep(polling_interval)
            
    except KeyboardInterrupt:
        print("\n🛑 Vault Sync stopped.")

if __name__ == "__main__":
    load_dotenv()
    # Can configure speed from .env, defaults to 30 seconds
    sync_vault(int(os.getenv("SYNC_INTERVAL", 30)))
