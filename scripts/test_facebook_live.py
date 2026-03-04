
import asyncio
import os
from dotenv import load_dotenv
from ai_employee.domains.social_media.facebook_adapter import FacebookAdapter
from ai_employee.domains.social_media.models import SocialPost, Platform

async def test_facebook_live():
    # Load environment variables
    load_dotenv()
    
    # Get credentials from env (provided by user)
    access_token = os.getenv("FACEBOOK_ACCESS_TOKEN")
    page_id = os.getenv("FACEBOOK_PAGE_ID")
    
    if not access_token or not page_id:
        print("❌ Error: FACEBOOK_ACCESS_TOKEN or FACEBOOK_PAGE_ID not found in .env")
        return

    print(f"🔄 Testing Facebook Live Posting for Page ID: {page_id}...")
    
    adapter = FacebookAdapter()
    
    # 1. Authenticate
    credentials = {
        "access_token": access_token,
        "page_id": page_id
    }
    
    is_authenticated = await adapter.authenticate(credentials)
    if not is_authenticated:
        print("\n❌ Authentication failed! Troubleshooting Tips:")
        print("1.  Did you copy the entire ACCESS TOKEN?")
        print(f"2.  Is your PAGE_ID correct ({page_id})?")
        print("3.  Does the token have 'pages_manage_posts' permission?")
        print("💡 Go back to Graph API Explorer, select your Page, and regenerate a fresh token.")
        return
    
    print("✅ Authenticated successfully!")

    # 2. Post Content
    test_post = SocialPost(
        platform=Platform.FACEBOOK,
        content="Hello! This is a test post from my Autonomous AI Employee. 🤖🚀 #AI #Automation #Hackathon",
        content_type="text"
    )
    
    try:
        post_id = await adapter.post_content(test_post)
        print(f"✅ Successfully posted to Facebook! Post ID: {post_id}")
        print(f"🔗 View it at: https://www.facebook.com/{post_id}")
    except Exception as e:
        print(f"❌ Failed to post: {e}")

if __name__ == "__main__":
    asyncio.run(test_facebook_live())
