#!/usr/bin/env python3
"""
Diagnose Odoo connection issues
"""

import subprocess
import sys

print("="*60)
print("ODOO CONNECTION DIAGNOSTICS")
print("="*60)

# Check if Odoo is running on port 8069
print("\n1. Checking if Odoo is running on port 8069...")
try:
    result = subprocess.run(['netstat', '-an'], capture_output=True, text=True)
    if ':8069' in result.stdout:
        print("[OK] Port 8069 is in use")
    else:
        print("[WARNING] Port 8069 not found in netstat output")
        print("Odoo might not be running or might use a different port")
except:
    print("[INFO] Could not check netstat")

# Check .env configuration
print("\n2. Current .env configuration:")
env_file = "../.env"
try:
    with open(env_file, 'r') as f:
        lines = f.readlines()
        for line in lines:
            if line.startswith('ODOO_'):
                print(f"  {line.strip()}")
except:
    print(f"[ERROR] Could not read {env_file}")

# Provide guidance
print("\n3. Common Issues and Solutions:")
print("   Issue: 'Database not found'")
print("   Solution: Create database at http://localhost:8069/web/database/manager")
print()
print("   Issue: 'Authentication failed'")
print("   Solution: Use admin/admin for local Odoo, or check credentials")
print()
print("   Issue: 'Connection refused'")
print("   Solution: Make sure Odoo is running (check port 8069)")

# Test with curl if available
print("\n4. Testing connectivity with curl...")
try:
    result = subprocess.run(['curl', '-s', 'http://localhost:8069'], capture_output=True, text=True)
    if result.returncode == 0:
        if 'odoo' in result.stdout.lower() or 'web' in result.stdout.lower():
            print("[OK] Odoo is responding at http://localhost:8069")
        else:
            print("[WARNING] Unexpected response from Odoo")
    else:
        print("[ERROR] Cannot connect to http://localhost:8069")
except:
    print("[INFO] curl not available or failed")

print("\n5. Next Steps:")
print("   1. Open http://localhost:8069 in your browser")
print("   2. Note the database name shown on login page")
print("   3. Update ODOO_DB in .env if needed")
print("   4. Run: python scripts/run_odoo_test.py")