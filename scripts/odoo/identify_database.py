#!/usr/bin/env python3
"""
Help identify the correct Odoo database name
"""

print("="*60)
print("ODOO DATABASE IDENTIFICATION")
print("="*60)

print("\nTo find your database name:")
print("1. Go to http://localhost:8069/web/database/manager")
print("2. Look at the list of databases")
print("3. Note the exact name of your database")
print("\nCommon database names might be:")
print(" - odoo")
print(" - hackathon_zero")
print(" - test")
print(" - admin")
print("\nOnce you know the database name, update .env:")
print("ODOO_DB=<your-database-name>")
print("\nThen run the test again.")

# Also check if they might be using a different port
print("\nIf you're not using port 8069, update .env:")
print("ODOO_URL=http://localhost:<your-port>")

# Instructions to check what's actually running
print("\nTo verify Odoo is running correctly:")
print("1. Open http://localhost:8069 in browser")
print("2. You should see a login page or database selector")
print("3. If you see a login page, note the database name shown")
print("4. If you see database list, pick or create your database")