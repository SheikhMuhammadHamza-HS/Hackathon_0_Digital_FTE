
import asyncio
import os
import sys
from dotenv import load_dotenv
from typing import List, Optional

# Add current directory to path
sys.path.append(os.getcwd())

from ai_employee.domains.social_media.facebook_adapter import FacebookAdapter, InstagramAdapter
from ai_employee.domains.social_media.models import SocialPost, Platform
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

async def interactive_post():
    load_dotenv()
    
    console.print(Panel.fit("[bold cyan]🤖 AI Employee Social Media Manager[/bold cyan]\n[italic]Let's publish something amazing![/italic]"))

    # 1. Platform Selection
    platform_choice = Prompt.ask(
        "Select social media platform",
        choices=["Facebook", "Instagram"],
        default="Facebook"
    )
    
    selected_platform = Platform.FACEBOOK if platform_choice == "Facebook" else Platform.INSTAGRAM

    # 2. Content Type Selection
    if selected_platform == Platform.INSTAGRAM:
        # Instagram requires visual content
        content_type = Prompt.ask("Select content type", choices=["image", "video"], default="image")
    else:
        content_type = Prompt.ask("Select content type", choices=["text", "image", "video"], default="text")

    # 3. Get Content from User
    content = Prompt.ask(f"Enter your [bold yellow]{platform_choice}[/bold yellow] post content/caption")
    
    media_url = None
    if content_type in ["image", "video"]:
        media_url = Prompt.ask("Enter the publicly accessible URL for your media (image/video)")

    # 4. Preview and Confirm
    console.print("\n[bold green]--- Post Preview ---[/bold green]")
    console.print(f"[bold]Platform:[/bold] {platform_choice}")
    console.print(f"[bold]Type:[/bold] {content_type}")
    console.print(f"[bold]Content:[/bold] {content}")
    if media_url:
        console.print(f"[bold]Media URL:[/bold] {media_url}")
    console.print("[bold green]--------------------[/bold green]\n")

    confirm = Prompt.ask("Do you want to publish this post?", choices=["yes", "no"], default="no")
    if confirm.lower() != "yes":
        console.print("[bold red]Post cancelled.[/bold red]")
        return

    # 5. Initialize Adapter and Post
    adapter = FacebookAdapter() if selected_platform == Platform.FACEBOOK else InstagramAdapter()
    
    # Credentials from .env
    credentials = {
        "access_token": os.getenv("FACEBOOK_ACCESS_TOKEN"),
        "page_id": os.getenv("FACEBOOK_PAGE_ID"),
        "instagram_user_id": os.getenv("INSTAGRAM_USER_ID")
    }

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description=f"Publishing to {platform_choice}...", total=None)
        
        try:
            # Authenticate
            auth_success = await adapter.authenticate(credentials)
            if not auth_success:
                console.print(f"[bold red]❌ Failed to authenticate with {platform_choice}. Check your .env[/bold red]")
                return

            # Create Post object
            post = SocialPost(
                platform=selected_platform,
                content=content,
                content_type=content_type
            )
            if media_url:
                setattr(post, 'media_url', media_url)

            # Post
            post_id = await adapter.post_content(post)
            console.print(f"\n[bold green]🎉 SUCCESS![/bold green] Your post is live on {platform_choice}!")
            console.print(f"[cyan]Post ID:[/cyan] {post_id}")
            
            if selected_platform == Platform.FACEBOOK:
                console.print(f"[link=https://www.facebook.com/{post_id}]🔗 Click here to view your post[/link]")

        except Exception as e:
            console.print(f"\n[bold red]❌ FULL ERROR DETAILS:[/bold red]\n{str(e)}")
            if hasattr(e, '__dict__'):
                console.print(f"[dim]{e.__dict__}[/dim]")

if __name__ == "__main__":
    asyncio.run(interactive_post())
