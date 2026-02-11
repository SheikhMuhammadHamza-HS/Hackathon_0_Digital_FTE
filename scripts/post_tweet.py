import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.services.playwright_x_service import PlaywrightXService
from src.services.dashboard_updater import DashboardUpdater

def post_custom_tweet():
    # If content passed as command line argument, use it
    if len(sys.argv) > 1:
        content = " ".join(sys.argv[1:])
    else:
        # Otherwise ask for input
        content = input("Enter the tweet you want to post: ")

    if not content:
        print("Error: No content provided.")
        return

    print(f"\n--- Posting to X ---")
    print(f"Content: {content}")
    
    service = PlaywrightXService()
    try:
        success = service.post_tweet(content)
        
        if success:
            print("\n✅ SUCCESS: Your tweet has been posted!")
            # Log to dashboard
            dashboard = DashboardUpdater()
            dashboard.append_entry(f"Manual X post: {content[:30]}...", "SUCCESS")
        else:
            print("\n❌ FAILURE: Could not post tweet. Check Logs/ for details.")
            dashboard = DashboardUpdater()
            dashboard.append_entry(f"Manual X post attempt", "FAILURE")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
    finally:
        service.close()

if __name__ == "__main__":
    post_custom_tweet()
