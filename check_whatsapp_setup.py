#!/usr/bin/env python3
"""Check WhatsApp Business API setup step by step."""

import os
import requests

def check_whatsapp_setup():
    """Verify WhatsApp Business API configuration."""
    print("WhatsApp Setup Verification")
    print("="*50)

    # Get credentials
    phone_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID', '')
    access_token = os.getenv('WHATSAPP_ACCESS_TOKEN', '')

    print(f"1. Credentials Check:")
    print(f"   Phone Number ID: {'SET' if phone_id else 'NOT_SET'}")
    print(f"   Access Token: {'SET' if access_token else 'NOT_SET'}")
    print()

    if not phone_id or not access_token:
        print("❌ Missing credentials!")
        return

    # Test basic API connection
    print("2. Testing API Connection...")
    try:
        # Test 1: Get user info (basic test)
        url = f"https://graph.facebook.com/v21.0/me"
        headers = {"Authorization": f"Bearer {access_token}"}

        response = requests.get(url, headers=headers)
        print(f"   Basic API test: {response.status_code}")

        if response.status_code == 200:
            print("   ✅ Basic API connection works")
        else:
            print(f"   ❌ Basic API failed: {response.text}")
            return

        # Test 2: Get phone numbers associated with account
        print("\n3. Checking WhatsApp Business Account...")
        url = f"https://graph.facebook.com/v21.0/{phone_id}"
        response = requests.get(url, headers=headers)

        print(f"   Phone number query: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("   ✅ Phone number found!")
            print(f"   Details: {data}")
        elif response.status_code == 400:
            error = response.json().get('error', {})
            print(f"   ❌ Error: {error.get('message', 'Unknown error')}")

            # Common error messages
            if 'OAuthException' in error.get('type', ''):
                print("\n   🔍 OAuth Error - Possible causes:")
                print("   - Token expired (regenerate from Graph API Explorer)")
                print("   - Wrong token type (use long-lived token)")
                print("   - Missing permissions")
            elif 'invalid' in error.get('message', '').lower():
                print("\n   🔍 Invalid Phone Number ID")
                print("   - Check the correct ID from WhatsApp Business settings")
                print("   - It should be a long number, not your phone number")
        else:
            print(f"   ❌ Unexpected response: {response.text}")

    except Exception as e:
        print(f"   ❌ Connection error: {e}")

    print("\n" + "="*50)
    print("Check complete!")

if __name__ == '__main__':
    check_whatsapp_setup()