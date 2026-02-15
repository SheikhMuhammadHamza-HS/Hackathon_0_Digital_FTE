import asyncio
import logging
import sys
import json
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.services.mcp_client import get_mcp_manager
from src.config.logging_config import setup_logging
from src.config.settings import settings  # Triggers load_dotenv

# Configure logging
setup_logging("INFO")
logger = logging.getLogger(__name__)

async def test_real_credentials():
    with open("tests/test_real_auth_results.txt", "w", encoding="utf-8") as output_file:
        def log(msg):
            print(msg)
            output_file.write(str(msg) + "\n")
            
        log("\n=== Testing MCP Servers with REAL Credentials ===\n")
        
        manager = get_mcp_manager()
        if not manager:
            log("❌ Failed to initialize MCP Manager")
            return

        # 1. Test Gmail Authentication
        log("📧 Testing Email MCP (Gmail)...")
        email_client = manager.get_client("email-mcp")
        if email_client:
            log("  ✅ Client initialized")
            try:
                log("  Attempting to fetch Gmail profile...")
                result = email_client.call_tool("get_profile", {})
                
                if result and not result.get('isError'):
                    content = result['content'][0]['text']
                    profile = json.loads(content)
                    log(f"  ✅ SUCCESS! Authenticated as: {profile.get('email_address')}")
                    log(f"  📊 Stats: {profile.get('messages_total')} messages, {profile.get('threads_total')} threads")
                else:
                    log(f"  ❌ Failed to fetch profile: {result}")
            except Exception as e:
                log(f"  ❌ Exception during call: {e}")
            finally:
                email_client.stop()
        else:
            log("  ❌ Could not initialize email-mcp client")

        log("\n------------------------------------------------\n")

        # 2. Test LinkedIn Authentication
        log("🔗 Testing LinkedIn MCP...")
        linkedin_client = manager.get_client("linkedin-mcp")
        if linkedin_client:
            log("  ✅ Client initialized")
            try:
                log("  Attempting to fetch LinkedIn profile...")
                result = linkedin_client.call_tool("get_profile", {})
                
                if result and not result.get('isError'):
                    content = result['content'][0]['text']
                    profile = json.loads(content)
                    first_name = profile.get('localized_first_name', 'Unknown')
                    last_name = profile.get('localized_last_name', '')
                    log(f"  ✅ SUCCESS! Authenticated as: {first_name} {last_name}")
                    log(f"  📝 Headline: {profile.get('headline')}")
                else:
                    try:
                        error_msg = result.get('content', [{'text': 'Unknown error'}])[0].get('text')
                    except:
                        error_msg = str(result)
                    log(f"  ❌ Failed to fetch profile: {error_msg}")
            except Exception as e:
                log(f"  ❌ Exception during call: {e}")
            finally:
                linkedin_client.stop()
        else:
            log("  ❌ Could not initialize linkedin-mcp client")

        log("\n================================================")

if __name__ == "__main__":
    asyncio.run(test_real_credentials())
