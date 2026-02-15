#!/usr/bin/env python3
"""Debug WhatsApp connectivity issues."""

import os
import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from services.mcp_client import get_mcp_manager

def debug_whatsapp():
    """Debug WhatsApp connection step by step."""
    print("WhatsApp Debug Tool")
    print("="*50)

    # Check environment variables
    phone_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID', 'NOT_SET')
    access_token = os.getenv('WHATSAPP_ACCESS_TOKEN', 'NOT_SET')

    print(f"1. Environment Variables:")
    print(f"   WHATSAPP_PHONE_NUMBER_ID: {'SET' if phone_id != 'NOT_SET' else 'NOT_SET'}")
    print(f"   WHATSAPP_ACCESS_TOKEN: {'SET' if access_token != 'NOT_SET' else 'NOT_SET'}")
    print()

    # Check if values look valid
    if phone_id != 'NOT_SET':
        print(f"2. Phone Number ID Analysis:")
        print(f"   Length: {len(phone_id)}")
        print(f"   Starts with digits: {phone_id[:5] if phone_id else 'Empty'}")
        print()

    if access_token != 'NOT_SET':
        print(f"3. Access Token Analysis:")
        print(f"   Length: {len(access_token)}")
        print(f"   Starts with: {access_token[:10]}..." if len(access_token) > 10 else access_token)
        print()

    # Test basic MCP connection
    print("4. Testing MCP Connection...")
    try:
        manager = get_mcp_manager()
        client = manager.get_client('whatsapp-mcp')

        if client:
            print("   ✓ WhatsApp MCP client obtained")

            # Test listing tools
            tools = client.list_tools()
            if tools:
                print(f"   ✓ Found {len(tools)} tools")
                for tool in tools:
                    print(f"     - {tool['name']}")
            else:
                print("   ✗ No tools found")

            # Test with a simple number format check
            print("\n5. Testing with proper phone format...")
            test_result = client.call_tool('send_message', {
                'to': '+14155551234',  # Valid US format
                'body': 'Test debug message'
            })

            if test_result:
                print(f"   Result: {test_result}")
                if test_result.get('isError'):
                    error_text = test_result.get('content', [{}])[0].get('text', 'Unknown error')
                    print(f"   Error Details: {error_text}")

                    # Common error patterns
                    if 'OAuthException' in error_text:
                        print("\n   🔍 OAuth Error Detected:")
                        print("   - Access token might be expired")
                        print("   - Token might not have WhatsApp permissions")
                        print("   - Try regenerating token from Facebook Developer Console")
                    elif 'phone_number' in error_text.lower():
                        print("\n   🔍 Phone Number Error:")
                        print("   - Ensure phone number is in E.164 format (+1234567890)")
                        print("   - Phone number must be registered with WhatsApp Business")
                    elif 'permission' in error_text.lower():
                        print("\n   🔍 Permission Error:")
                        print("   - Check WhatsApp Business API permissions")
                        print("   - Ensure phone number is verified")
                else:
                    print("   ✓ Message sent successfully!")
            else:
                print("   ✗ No response from server")
        else:
            print("   ✗ Could not get WhatsApp MCP client")

    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*50)
    print("Debug Complete")

if __name__ == '__main__':
    debug_whatsapp()