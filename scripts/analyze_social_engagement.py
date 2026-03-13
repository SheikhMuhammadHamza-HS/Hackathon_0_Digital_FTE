
import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_employee.domains.social_media.facebook_adapter import FacebookAdapter
from ai_employee.domains.social_media.models import Platform
from src.config.logging_config import get_logger

logger = get_logger("SocialEngagement")

async def analyze_engagement():
    load_dotenv()
    
    access_token = os.getenv("FACEBOOK_ACCESS_TOKEN")
    page_id = os.getenv("FACEBOOK_PAGE_ID")
    
    if not access_token or not page_id:
        logger.error("Missing FACEBOOK_ACCESS_TOKEN or FACEBOOK_PAGE_ID in .env")
        return

    adapter = FacebookAdapter()
    credentials = {
        "access_token": access_token,
        "page_id": page_id
    }
    
    if not await adapter.authenticate(credentials):
        return

    print(f"📊 Analyzing Engagement for Facebook Page ID: {page_id}...")
    
    posts = await adapter.get_recent_posts(limit=10)
    if not posts:
        print("No recent posts found to analyze.")
        return

    analysis_report = f"# 📱 Social Media Engagement Summary\n"
    analysis_report += f"**Generated on:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    analysis_report += "| Date | Post Content | Likes | Comments | Shares | Total Engagement |\n"
    analysis_report += "|---|---|---|---|---|---|\n"

    total_likes = 0
    total_comments = 0
    total_shares = 0

    for post in posts:
        post_id = post.get('id')
        message = post.get('message', 'No text content')[:50] + "..."
        created_time = post.get('created_time', '').split('T')[0]
        
        stats = await adapter.get_engagement_stats(post_id)
        likes = stats.get('likes', 0)
        comments = stats.get('comments', 0)
        shares = stats.get('shares', 0)
        total = likes + comments + shares
        
        total_likes += likes
        total_comments += comments
        total_shares += shares
        
        analysis_report += f"| {created_time} | {message} | {likes} | {comments} | {shares} | {total} |\n"

    analysis_report += f"\n## 📈 Aggregated Stats\n"
    analysis_report += f"- **Total Posts Analyzed:** {len(posts)}\n"
    analysis_report += f"- **Total Likes:** {total_likes}\n"
    analysis_report += f"- **Total Comments:** {total_comments}\n"
    analysis_report += f"- **Total Shares:** {total_shares}\n"
    analysis_report += f"- **Avg Engagement per Post:** {(total_likes + total_comments + total_shares) / len(posts):.2f}\n"

    # Save report to Vault
    report_path = Path("Vault/Reports/Social_Engagement_Summary.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(analysis_report, encoding='utf-8')
    
    print(f"✅ Engagement report generated at: {report_path.resolve()}")
    print("-" * 50)
    print(analysis_report)

if __name__ == "__main__":
    asyncio.run(analyze_engagement())
