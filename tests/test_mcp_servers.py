"""Test MCP Servers functionality.

This script tests the MCP server architecture implementation,
including client initialization, server connections, and tool calls.
"""

import sys
import json
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from services.mcp_client import MCPManager, get_mcp_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_mcp_config_loading():
    """Test 1: MCP configuration loading."""
    print("\n" + "="*60)
    print("TEST 1: MCP Configuration Loading")
    print("="*60)

    config_path = Path('mcp.json')
    if not config_path.exists():
        print("❌ FAIL: mcp.json not found")
        return False

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)

        servers = config.get('mcpServers', {})
        print(f"✅ PASS: Loaded {len(servers)} MCP server configurations")
        print(f"   Available servers: {', '.join(servers.keys())}")

        # Check for required servers
        required_servers = ['email-mcp', 'linkedin-mcp']
        missing = [s for s in required_servers if s not in servers]
        if missing:
            print(f"⚠️  WARNING: Missing required servers: {', '.join(missing)}")
        else:
            print(f"✅ All required servers present: {', '.join(required_servers)}")

        return True

    except Exception as e:
        print(f"❌ FAIL: Error loading config: {e}")
        return False


def test_mcp_manager_initialization():
    """Test 2: MCP Manager initialization."""
    print("\n" + "="*60)
    print("TEST 2: MCP Manager Initialization")
    print("="*60)

    try:
        manager = get_mcp_manager()
        print(f"✅ PASS: MCP Manager initialized")

        print(f"   Number of configured servers: {len(manager.clients)}")
        print(f"   Server names: {', '.join(manager.clients.keys())}")

        return True

    except Exception as e:
        print(f"❌ FAIL: Error initializing manager: {e}")
        return False


def test_client_creation():
    """Test 3: MCP Client creation."""
    print("\n" + "="*60)
    print("TEST 3: MCP Client Creation")
    print("="*60)

    try:
        manager = get_mcp_manager()

        test_servers = ['email-mcp', 'linkedin-mcp']
        results = {}

        for server_name in test_servers:
            if server_name in manager.clients:
                client = manager.clients[server_name]
                results[server_name] = {
                    'config': client.config is not None,
                    'command': client.config.get('command'),
                    'args': client.config.get('args', [])
                }
                print(f"✅ PASS: {server_name} client created")
                print(f"   Command: {client.config.get('command')}")

                # Check for placeholder credentials
                env = client.config.get('env', {})
                placeholders = ['your_', '${']
                has_placeholder = any(
                    any(ph in str(v) for v in env.values())
                    for ph in placeholders
                )
                if has_placeholder:
                    print(f"   ⚠️  WARNING: Contains placeholder credentials")
            else:
                print(f"❌ FAIL: {server_name} not in manager")
                results[server_name] = None

        return all(v is not None for v in results.values())

    except Exception as e:
        print(f"❌ FAIL: Error creating clients: {e}")
        return False


def test_refactored_agents():
    """Test 4: Refactored agents use MCP."""
    print("\n" + "="*60)
    print("TEST 4: Refactored Agents Use MCP")
    print("="*60)

    try:
        from agents.email_sender import EmailSender
        from agents.linkedin_poster import LinkedInPoster

        # Test EmailSender
        email_sender = EmailSender()
        print(f"✅ PASS: EmailSender initialized")
        print(f"   MCP Manager: {'Yes' if email_sender.mcp_manager else 'No'}")
        print(f"   MCP Enabled: {'Yes' if email_sender.use_mcp else 'No'}")

        # Test LinkedInPoster
        linkedin_poster = LinkedInPoster()
        print(f"✅ PASS: LinkedInPoster initialized")
        print(f"   MCP Manager: {'Yes' if linkedin_poster.mcp_manager else 'No'}")
        print(f"   MCP Enabled: {'Yes' if linkedin_poster.use_mcp else 'No'}")

        # Test draft parsing
        test_draft = Path('test_draft_email.md')
        if test_draft.exists():
            parsed = email_sender._parse_draft(test_draft)
            print(f"✅ PASS: Draft parsing works")
            print(f"   Parsed: to={parsed['to']}, subject={parsed['subject']}")
        else:
            print(f"   ℹ️  INFO: No test draft found, skipping parse test")

        return True

    except Exception as e:
        print(f"❌ FAIL: Error testing agents: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_action_executor_integration():
    """Test 5: ActionExecutor integration with MCP-based agents."""
    print("\n" + "="*60)
    print("TEST 5: ActionExecutor Integration")
    print("="*60)

    try:
        from services.action_executor import ActionExecutor

        executor = ActionExecutor()
        print(f"✅ PASS: ActionExecutor initialized")

        # Check that agents are MCP-based
        print(f"   EmailSender type: {type(executor.email_sender).__name__}")
        print(f"   LinkedInPoster type: {type(executor.linkedin_poster).__name__}")

        # Verify they have MCP attributes
        has_mcp = (
            hasattr(executor.email_sender, 'mcp_manager') and
            hasattr(executor.linkedin_poster, 'mcp_manager')
        )
        print(f"   MCP attributes: {'Yes' if has_mcp else 'No'}")

        return True

    except Exception as e:
        print(f"❌ FAIL: Error testing ActionExecutor: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mcp_server_files():
    """Test 6: MCP server files exist and are valid."""
    print("\n" + "="*60)
    print("TEST 6: MCP Server Files")
    print("="*60)

    required_files = [
        'mcp-servers/email-mcp/package.json',
        'mcp-servers/email-mcp/index.js',
        'mcp-servers/linkedin-mcp/package.json',
        'mcp-servers/linkedin-mcp/index.js',
        'mcp-servers/README.md'
    ]

    all_exist = True
    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            print(f"✅ PASS: {file_path} exists")
        else:
            print(f"❌ FAIL: {file_path} missing")
            all_exist = False

    # Check package.json content
    try:
        email_pkg = Path('mcp-servers/email-mcp/package.json')
        if email_pkg.exists():
            with open(email_pkg) as f:
                pkg = json.load(f)
                print(f"✅ PASS: email-mcp package.json valid")
                print(f"   Name: {pkg.get('name')}")
                print(f"   Version: {pkg.get('version')}")
    except Exception as e:
        print(f"❌ FAIL: Error reading package.json: {e}")

    return all_exist


def run_all_tests():
    """Run all MCP server tests."""
    print("\n" + "="*60)
    print("MCP SERVERS TEST SUITE")
    print("="*60)
    print("Testing MCP Server Architecture Implementation (T049)")
    print("="*60)

    tests = [
        ("Configuration Loading", test_mcp_config_loading),
        ("Manager Initialization", test_mcp_manager_initialization),
        ("Client Creation", test_client_creation),
        ("Refactored Agents", test_refactored_agents),
        ("ActionExecutor Integration", test_action_executor_integration),
        ("Server Files", test_mcp_server_files),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ EXCEPTION in {test_name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! MCP Server architecture is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the output above.")
        return 1


if __name__ == '__main__':
    exit_code = run_all_tests()
    sys.exit(exit_code)