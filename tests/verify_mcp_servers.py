import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.services.mcp_client import get_mcp_manager
from src.config.logging_config import setup_logging

# Configure logging
setup_logging("INFO")
logger = logging.getLogger(__name__)

async def verify_servers():
    with open("tests/verify_mcp_results.txt", "w", encoding="utf-8") as output_file:
        def log(msg):
            print(msg)
            output_file.write(msg + "\n")
            
        log("\n=== Verifying MCP Servers ===\n")
        
        manager = get_mcp_manager()
        if not manager:
            log("❌ Failed to initialize MCP Manager")
            return

        servers_to_test = ["email-mcp", "linkedin-mcp"]
        
        for server_name in servers_to_test:
            log(f"Testing {server_name}...")
            
            try:
                client = manager.get_client(server_name)
                if not client:
                    log(f"  ❌ Failed to get client for {server_name}")
                    continue
                    
                log(f"  ✅ Client initialized for {server_name}")
                
                # Try to list tools
                log(f"  Attempting to list tools for {server_name}...")
                tools = client.list_tools()
                
                if tools is not None:
                    log(f"  ✅ Successfully listed {len(tools)} tools:")
                    for tool in tools:
                        log(f"    - {tool['name']}: {tool.get('description', 'No description')}")
                else:
                    log(f"  ❌ Failed to list tools for {server_name}")
                    
                # Stop the client
                client.stop()
                log(f"  Server {server_name} stopped.\n")
            except Exception as e:
                log(f"  ❌ Exception testing {server_name}: {e}")

if __name__ == "__main__":
    asyncio.run(verify_servers())
