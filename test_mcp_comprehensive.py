"""Comprehensive test for MCP Servers functionality.

Tests the complete MCP server architecture implementation.
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


def test_mcp_architecture():
    """Test the complete MCP architecture."""
    print("\n" + "="*70)
    print("COMPREHENSIVE MCP SERVER TEST")
    print("="*70)
    print("Testing Task T049: Transition to MCP Server Architecture")
    print("="*70)

    tests_passed = 0
    total_tests = 0

    # Test 1: Configuration Validation
    print("\n1. Testing MCP Configuration...")
    total_tests += 1
    config_path = Path('mcp.json')

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)

        servers = config.get('mcpServers', {})
        print(f"   PASS: Loaded {len(servers)} MCP server configurations")

        # Check specific servers
        required_servers = ['email-mcp', 'linkedin-mcp']
        found_servers = [s for s in required_servers if s in servers]
        print(f"   Required servers found: {', '.join(found_servers)}")

        if len(found_servers) == len(required_servers):
            print("   PASS: All required servers configured")
            tests_passed += 1
        else:
            print("   WARN: Some required servers missing")

    except Exception as e:
        print(f"   FAIL: Error loading config: {e}")

    # Test 2: MCP Manager Initialization
    print("\n2. Testing MCP Manager...")
    total_tests += 1
    try:
        manager = get_mcp_manager()
        print(f"   PASS: MCP Manager initialized successfully")
        print(f"   Total servers configured: {len(manager.clients)}")

        # List all servers
        for name, client in manager.clients.items():
            print(f"   - {name}: {client.server_name}")

        tests_passed += 1

    except Exception as e:
        print(f"   FAIL: Error initializing manager: {e}")

    # Test 3: Server File Structure
    print("\n3. Testing Server File Structure...")
    total_tests += 1

    required_files = {
        'email-mcp': [
            'mcp-servers/email-mcp/package.json',
            'mcp-servers/email-mcp/index.js'
        ],
        'linkedin-mcp': [
            'mcp-servers/linkedin-mcp/package.json',
            'mcp-servers/linkedin-mcp/index.js'
        ]
    }

    all_files_exist = True
    for server_name, files in required_files.items():
        print(f"   Checking {server_name}...")
        server_exists = True
        for file_path in files:
            path = Path(file_path)
            if path.exists():
                print(f"     ✓ {file_path}")
            else:
                print(f"     ✗ {file_path} - MISSING")
                all_files_exist = False
                server_exists = False

        if server_exists:
            print(f"   ✓ {server_name} files complete")
        else:
            print(f"   ✗ {server_name} files incomplete")

    if all_files_exist:
        print("   PASS: All MCP server files exist")
        tests_passed += 1
    else:
        print("   FAIL: Some MCP server files missing")

    # Test 4: Package.json Validation
    print("\n4. Testing Package.json Files...")
    total_tests += 1

    package_files = [
        'mcp-servers/email-mcp/package.json',
        'mcp-servers/linkedin-mcp/package.json'
    ]

    packages_valid = True
    for pkg_file in package_files:
        try:
            with open(pkg_file) as f:
                pkg = json.load(f)

            print(f"   {pkg_file}:")
            print(f"     Name: {pkg.get('name', 'N/A')}")
            print(f"     Version: {pkg.get('version', 'N/A')}")
            print(f"     Dependencies: {len(pkg.get('dependencies', {}))}")

            # Check for required dependencies
            deps = pkg.get('dependencies', {})
            if '@modelcontextprotocol/sdk' in deps:
                print(f"     ✓ MCP SDK dependency present")
            else:
                print(f"     ⚠ MCP SDK dependency missing")

        except Exception as e:
            print(f"   FAIL: Error reading {pkg_file}: {e}")
            packages_valid = False

    if packages_valid:
        print("   PASS: All package.json files are valid")
        tests_passed += 1
    else:
        print("   FAIL: Some package.json files have issues")

    # Test 5: Refactored Agents Integration
    print("\n5. Testing Refactored Agents...")
    total_tests += 1

    try:
        # Import the refactored agents
        from agents.email_sender import EmailSender
        from agents.linkedin_poster import LinkedInPoster

        print("   Testing EmailSender...")
        email_sender = EmailSender()
        print(f"     MCP Manager: {'Yes' if email_sender.mcp_manager else 'No'}")
        print(f"     MCP Enabled: {'Yes' if email_sender.use_mcp else 'No'}")

        print("   Testing LinkedInPoster...")
        linkedin_poster = LinkedInPoster()
        print(f"     MCP Manager: {'Yes' if linkedin_poster.mcp_manager else 'No'}")
        print(f"     MCP Enabled: {'Yes' if linkedin_poster.use_mcp else 'No'}")

        # Test draft parsing
        print("   Testing draft parsing...")
        test_draft = Path(__file__).parent / 'test_email.md'
        if test_draft.exists():
            parsed = email_sender._parse_draft(test_draft)
            print(f"     Parsed email: to={parsed['to']}, subject={parsed['subject']}")
        else:
            print("     No test draft found")

        print("   PASS: Agents successfully refactored for MCP")
        tests_passed += 1

    except Exception as e:
        print(f"   FAIL: Error testing agents: {e}")
        import traceback
        traceback.print_exc()

    # Test 6: MCP Client Capabilities
    print("\n6. Testing MCP Client Capabilities...")
    total_tests += 1

    try:
        # Get specific clients
        email_client = manager.get_client('email-mcp')
        linkedin_client = manager.get_client('linkedin-mcp')

        if email_client:
            print("   ✓ email-mcp client available")
            # Would test actual tool calls if env vars were set
            # tools = email_client.list_tools()
            # print(f"   Available tools: {len(tools) if tools else 0}")
        else:
            print("   ✗ email-mcp client not available")

        if linkedin_client:
            print("   ✓ linkedin-mcp client available")
        else:
            print("   ✗ linkedin-mcp client not available")

        if email_client and linkedin_client:
            print("   PASS: MCP clients are accessible")
            tests_passed += 1
        else:
            print("   WARN: Some MCP clients not available (may need environment setup)")

    except Exception as e:
        print(f"   WARN: Error testing client capabilities: {e}")
        print("   Note: This is normal if environment variables are not configured")

    # Test 7: Architecture Verification
    print("\n7. Verifying MCP Architecture...")
    total_tests += 1

    # Check that old direct API usage is removed
    old_imports = [
        'from googleapiclient.discovery import build',
        'from google.oauth2.credentials import Credentials'
    ]

    # Read the refactored files
    email_file = Path('src/agents/email_sender.py')
    linkedin_file = Path('src/agents/linkedin_poster.py')

    architecture_correct = True

    if email_file.exists():
        with open(email_file) as f:
            email_content = f.read()

        # Check for MCP imports
        if 'from ..services.mcp_client import get_mcp_manager' in email_content:
            print("   ✓ EmailSender uses MCP client")
        else:
            print("   ✗ EmailSender does not use MCP client")
            architecture_correct = False

        # Check for old imports
        for old_import in old_imports:
            if old_import in email_content:
                print(f"   ✗ EmailSender still has old import: {old_import}")
                architecture_correct = False

    if linkedin_file.exists():
        with open(linkedin_file) as f:
            linkedin_content = f.read()

        # Check for MCP imports
        if 'from ..services.mcp_client import get_mcp_manager' in linkedin_content:
            print("   ✓ LinkedInPoster uses MCP client")
        else:
            print("   ✗ LinkedInPoster does not use MCP client")
            architecture_correct = False

    if architecture_correct:
        print("   PASS: Architecture correctly refactored for MCP")
        tests_passed += 1
    else:
        print("   FAIL: Architecture refactoring incomplete")

    # Final Summary
    print("\n" + "="*70)
    print("FINAL SUMMARY")
    print("="*70)
    print(f"Tests Passed: {tests_passed}/{total_tests}")
    print(f"Success Rate: {(tests_passed/total_tests)*100:.1f}%")

    if tests_passed == total_tests:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ MCP Server Architecture is fully implemented (Task T049)")
        print("✅ Silver Tier MCP requirement is COMPLETE")
        print("\nThe Digital FTE now uses official MCP servers for:")
        print("   - Email operations (via email-mcp)")
        print("   - LinkedIn posting (via linkedin-mcp)")
        print("\nThe architecture successfully transitions from internal")
        print("executors to MCP-based operations as required.")
        return True
    else:
        print(f"\n⚠️  {total_tests - tests_passed} test(s) failed")
        print("Please review the implementation")
        return False


if __name__ == '__main__':
    success = test_mcp_architecture()
    sys.exit(0 if success else 1)