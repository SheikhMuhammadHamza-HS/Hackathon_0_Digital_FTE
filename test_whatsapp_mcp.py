#!/usr/bin/env python3
"""Test WhatsApp MCP server directly."""

import sys
import json
import subprocess
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from services.mcp_client import MCPClient

def test_whatsapp_mcp():
    """Test WhatsApp MCP server functionality."""
    print("Testing WhatsApp MCP Server...")
    print("="*50)

    # Check environment variables
    phone_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID', 'test_phone_id')
    access_token = os.getenv('WHATSAPP_ACCESS_TOKEN', 'test_token')

    print(f"Phone Number ID: {phone_id}")
    print(f"Access Token: {'Set' if access_token != 'test_token' else 'Not Set'}")
    print()

    try:
        # Create MCP client directly
        config = {
            "command": "node",
            "args": ["mcp-servers/whatsapp-mcp/index.js"],
            "env": {
                "WHATSAPP_PHONE_NUMBER_ID": phone_id,
                "WHATSAPP_ACCESS_TOKEN": access_token
            }
        }

        client = MCPClient("whatsapp-mcp", config)
        print("Starting WhatsApp MCP server...")

        if client.start():
            print("PASS: MCP server started successfully")

            # Test listing tools
            print("\nListing available tools...")
            tools = client.list_tools()
            if tools:
                print(f"Found {len(tools)} tools:")
                for tool in tools:
                    print(f"  - {tool['name']}: {tool['description']}")
            else:
                print("No tools found or server not responding")

            # Test sending a message (with mock data)
            print("\nTesting send_message tool...")
            result = client.call_tool('send_message', {
                'to': '+1234567890',
                'body': 'Test message from MCP server test'
            })

            if result:
                print(f"Result: {result}")
                if result.get('isError'):
                    print(f"Error: {result.get('content', [{}])[0].get('text', 'Unknown error')}")
                else:
                    print("PASS: Message sent successfully")
            else:
                print("✗ No response from server")

        else:
            print("FAIL: Failed to start MCP server")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'client' in locals():
            client.stop()
            print("\nMCP server stopped")

if __name__ == '__main__':
    test_whatsapp_mcp()