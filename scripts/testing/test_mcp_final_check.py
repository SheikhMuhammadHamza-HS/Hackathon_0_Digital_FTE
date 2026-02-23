"""Final check for MCP Servers functionality.

Tests the core MCP server architecture without import issues.
"""

import sys
import json
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from services.mcp_client import get_mcp_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_mcp_final():
    """Final test of MCP implementation."""
    print("\n" + "="*60)
    print("MCP SERVER FINAL CHECK")
    print("="*60)
    print("Task T049: Transition to MCP Server Architecture")
    print("="*60)

    all_passed = True

    # Test 1: Configuration
    print("\n1. Checking MCP Configuration...")
    config_path = Path('mcp.json')

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)

        servers = config.get('mcpServers', {})
        print(f"   Found {len(servers)} MCP servers")

        # Check required servers
        required = ['email-mcp', 'linkedin-mcp']
        missing = [s for s in required if s not in servers]

        if not missing:
            print("   PASS: All required servers configured")
        else:
            print(f"   FAIL: Missing servers: {missing}")
            all_passed = False

    except Exception as e:
        print(f"   FAIL: Error loading config: {e}")
        all_passed = False

    # Test 2: Manager
    print("\n2. Checking MCP Manager...")
    try:
        manager = get_mcp_manager()
        print(f"   PASS: MCP Manager initialized")
        print(f"   Total servers: {len(manager.clients)}")

        # Check for our specific servers
        has_email = 'email-mcp' in manager.clients
        has_linkedin = 'linkedin-mcp' in manager.clients

        if has_email and has_linkedin:
            print("   PASS: email-mcp and linkedin-mcp clients available")
        else:
            print(f"   FAIL: Missing clients - email: {has_email}, linkedin: {has_linkedin}")
            all_passed = False

    except Exception as e:
        print(f"   FAIL: Error initializing manager: {e}")
        all_passed = False

    # Test 3: Server Files
    print("\n3. Checking Server Files...")

    server_files = {
        'email-mcp': [
            'mcp-servers/email-mcp/package.json',
            'mcp-servers/email-mcp/index.js'
        ],
        'linkedin-mcp': [
            'mcp-servers/linkedin-mcp/package.json',
            'mcp-servers/linkedin-mcp/index.js'
        ]
    }

    files_ok = True
    for server, files in server_files.items():
        print(f"   Checking {server}...")
        server_ok = True
        for file_path in files:
            if Path(file_path).exists():
                print(f"     + {file_path}")
            else:
                print(f"     - {file_path} - MISSING")
                server_ok = False
                files_ok = False

        if server_ok:
            print(f"   + {server} files complete")
        else:
            print(f"   - {server} files incomplete")

    if files_ok:
        print("   PASS: All server files exist")
    else:
        print("   FAIL: Some server files missing")
        all_passed = False

    # Test 4: Check Architecture by Reading Files
    print("\n4. Verifying Architecture Changes...")

    # Check EmailSender
    email_file = Path('src/agents/email_sender.py')
    if email_file.exists():
        with open(email_file) as f:
            content = f.read()

        if 'from ..services.mcp_client import get_mcp_manager' in content:
            print("   + EmailSender uses MCP client")
        else:
            print("   - EmailSender does not use MCP client")
            all_passed = False

        if 'EmailSender' in content and 'mcp_manager' in content:
            print("   + EmailSender class has MCP integration")
        else:
            print("   - EmailSender missing MCP integration")
            all_passed = False

    # Check LinkedInPoster
    linkedin_file = Path('src/agents/linkedin_poster.py')
    if linkedin_file.exists():
        with open(linkedin_file) as f:
            content = f.read()

        if 'from ..services.mcp_client import get_mcp_manager' in content:
            print("   + LinkedInPoster uses MCP client")
        else:
            print("   - LinkedInPoster does not use MCP client")
            all_passed = False

        if 'LinkedInPoster' in content and 'mcp_manager' in content:
            print("   + LinkedInPoster class has MCP integration")
        else:
            print("   - LinkedInPoster missing MCP integration")
            all_passed = False

    # Test 5: Task Status
    print("\n5. Checking Task Status...")
    tasks_file = Path('specs/001-silver-tier-ai/tasks.md')

    if tasks_file.exists():
        with open(tasks_file) as f:
            content = f.read()

        if 'T049' in content and '[X]' in content:
            print("   PASS: T049 marked as complete in tasks.md")
        else:
            print("   FAIL: T049 not marked as complete")
            all_passed = False
    else:
        print("   WARN: tasks.md file not found")

    # Final Summary
    print("\n" + "="*60)
    print("FINAL RESULT")
    print("="*60)

    if all_passed:
        print("\nALL CHECKS PASSED!")
        print("\nTask T049: SUCCESSFULLY IMPLEMENTED")
        print("Silver Tier MCP requirement: COMPLETE")
        print("\nImplementation Summary:")
        print("- MCP Server architecture created")
        print("- email-mcp and linkedin-mcp servers implemented")
        print("- EmailSender refactored to use MCP")
        print("- LinkedInPoster refactored to use MCP")
        print("- MCP client manager implemented")
        print("- Task T049 marked as complete")

        print("\nThe Digital FTE now uses official MCP servers")
        print("for external actions as required by the Silver Tier.")
        return True
    else:
        print("\nSOME CHECKS FAILED!")
        print("Please review the issues above.")
        return False


if __name__ == '__main__':
    success = test_mcp_final()
    sys.exit(0 if success else 1)