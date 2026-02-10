import logging
from pathlib import Path
from ..config import settings
from ..utils.security import is_safe_path

logger = logging.getLogger(__name__)

class XPoster:
    """Posts drafts to X (Twitter).
    
    Currently operates in mock mode. In a real scenario, this would use 
    tweepy or raw requests to the X v2 API.
    """

    def __init__(self):
        # Placeholders for X API credentials
        self.api_key = getattr(settings, "X_API_KEY", None)
        self.api_secret = getattr(settings, "X_API_SECRET", None)
        self.access_token = getattr(settings, "X_ACCESS_TOKEN", None)
        self.access_secret = getattr(settings, "X_ACCESS_SECRET", None)

        if all([self.api_key, self.api_secret, self.access_token, self.access_secret]):
            logger.info("XPoster configured with API keys (Real API calls not yet implemented)")
        else:
            logger.warning("XPoster: Missing credentials. Operating in mock mode.")

    def post_draft(self, draft_path: Path) -> bool:
        """Post the draft to X.
        
        Args:
            draft_path: Absolute path to the approved markdown draft.
            
        Returns:
            bool: True if successful (or mock success), False otherwise.
        """
        try:
            base_dir = Path(settings.APPROVED_PATH)
            if not is_safe_path(str(draft_path), str(base_dir)):
                logger.error("Unsafe draft path detected: %s", draft_path)
                return False

            content = draft_path.read_text(encoding="utf-8")
            
            # Clean content (remove frontmatter if present)
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    content = parts[2].strip()

            logger.info(f"MOCK X POST: Posting to X...")
            print(f"\n--- MOCK X POST START ---")
            print(f"Content: {content[:280]}...") # X limit is ~280 for basic
            print(f"--- MOCK X POST END ---\n")
            
            logger.info("Successfully 'posted' to X (Mock)")
            return True
        except Exception as e:
            logger.error(f"Failed to post to X: {e}")
            return False
