import logging
import tweepy
from pathlib import Path
from ..config import settings
from ..utils.security import is_safe_path
from ..services.playwright_x_service import PlaywrightXService

logger = logging.getLogger(__name__)

class XPoster:
    """Posts drafts to X (Twitter) using the v2 API (Tweepy) or Playwright fallback.
    
    The agent first attempts to use the official X API via Tweepy. If credentials
    are missing or the API call fails, it falls back to Playwright browser automation.
    """

    def __init__(self):
        # Retrieve X API credentials from settings
        self.api_key = getattr(settings, "X_API_KEY", None)
        self.api_secret = getattr(settings, "X_API_SECRET", None)
        self.access_token = getattr(settings, "X_ACCESS_TOKEN", None)
        self.access_secret = getattr(settings, "X_ACCESS_SECRET", None)

        self.client = None
        self.playwright_service = PlaywrightXService()
        
        if all([self.api_key, self.api_secret, self.access_token, self.access_secret]):
            try:
                # Initialize Tweepy Client for X API v2
                self.client = tweepy.Client(
                    consumer_key=self.api_key,
                    consumer_secret=self.api_secret,
                    access_token=self.access_token,
                    access_token_secret=self.access_secret
                )
                logger.info("XPoster: initialized real Tweepy client.")
            except Exception as e:
                logger.error(f"XPoster: Failed to initialize Tweepy client: {e}")
                self.client = None
        else:
            logger.warning("XPoster: Missing API credentials. Will default to Playwright.")

    def post_draft(self, draft_path: Path) -> bool:
        """Post the draft content to X.
        
        Args:
            draft_path: Absolute path to the approved markdown draft.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            base_dir = Path(settings.APPROVED_PATH)
            if not is_safe_path(str(draft_path), str(base_dir)):
                logger.error("Unsafe draft path detected: %s", draft_path)
                return False

            content = draft_path.read_text(encoding="utf-8")
            
            # Clean content (remove frontmatter/metadata if present)
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    content = parts[2].strip()
            
            # Additional cleaning for common headers
            lines = content.splitlines()
            cleaned_lines = []
            for line in lines:
                if not any(header in line.lower() for header in ["subject:", "platform:", "to:"]):
                    cleaned_lines.append(line)
            content = "\n".join(cleaned_lines).strip()

            if not content:
                logger.error("XPoster: No content to post in %s", draft_path.name)
                return False

            # Limit to 280 characters for X
            tweet_text = content[:280]

            # 1. Try API first if configured
            if self.client:
                try:
                    logger.info("XPoster: Attempting to post via real API...")
                    response = self.client.create_tweet(text=tweet_text)
                    tweet_id = response.data.get('id')
                    logger.info(f"XPoster: Successfully posted tweet via API! ID: {tweet_id}")
                    return True
                except Exception as api_err:
                    logger.warning(f"XPoster: API posting failed: {api_err}. Falling back to Playwright.")
            
            # 2. Fallback to Playwright automation
            logger.info("XPoster: Attempting to post via Playwright automation...")
            success = self.playwright_service.post_tweet(content)
            if success:
                logger.info("XPoster: Successfully posted tweet via Playwright!")
                return True
            else:
                logger.error("XPoster: Both API and Playwright posting failed.")
                return False

        except Exception as e:
            logger.error(f"XPoster: Unexpected error: {e}")
            return False
