import os
import sys
import logging
from pathlib import Path

# Add project root to sys.path
sys.path.append(os.getcwd())

from src.config.settings import settings
from src.agents.x_poster import XPoster

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_consolidated_x_poster():
    print("Testing Consolidated XPoster...")
    poster = XPoster()
    
    # Create a temporary test draft in the APPROVED directory
    approved_dir = Path(settings.APPROVED_PATH)
    approved_dir.mkdir(parents=True, exist_ok=True)
    test_draft = approved_dir / "temp_x_test.md"
    
    test_draft.write_text("""---
Subject: Consolidated Test
Platform: x
To: public
---
Testing the consolidated XPoster from my Digital FTE Agent! 🚀 This post uses the new Playwright fallback logic. #Automation #Python #AI
""", encoding="utf-8")

    try:
        print(f"Processing draft: {test_draft.name}")
        # Note: This will attempt API first, then Playwright.
        success = poster.post_draft(test_draft)
        
        if success:
            print("SUCCESS: XPoster successfully processed the draft.")
        else:
            print("FAILURE: XPoster failed to process the draft. Check Logs for screenshots.")
    except Exception as e:
        print(f"CRITICAL ERROR in verification script: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if test_draft.exists():
            test_draft.unlink()

if __name__ == "__main__":
    test_consolidated_x_poster()
