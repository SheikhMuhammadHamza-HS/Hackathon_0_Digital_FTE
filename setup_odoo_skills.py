"""
Setup script for Odoo skills integration.
"""

import os
from pathlib import Path


def create_odoo_env():
    """Create .env file with Odoo configuration."""
    env_path = Path("ai_employee/.env")

    if env_path.exists():
        content = env_path.read_text()
    else:
        content = ""

    # Add Odoo configuration if not present
    odoo_config = """
# Odoo Configuration (for skills)
ODOO_URL=http://localhost:8069
ODOO_DB=odoo
ODOO_USERNAME=admin
ODOO_PASSWORD=admin
"""

    if "ODOO_URL" not in content:
        content += odoo_config
        env_path.write_text(content)
        print("Odoo configuration added to .env")
    else:
        print("Odoo configuration already exists in .env")


def create_vault_structure():
    """Create required Vault directories."""
    vault = Path("Vault")

    directories = [
        "Inbox",
        "Needs_Action",
        "Pending_Approval",
        "Approved",
        "Rejected",
        "Done",
        "Logs",
        "Reports",
        "Archive",
        "Clients",
        "Accounting"
    ]

    for dir_name in directories:
        dir_path = vault / dir_name
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {dir_path}")


def create_sample_client():
    """Create a sample client file."""
    client_file = Path("Vault/Clients/Test Client.md")

    if not client_file.exists():
        content = """---
name: Test Client
payment_terms: 30
tax_id: 12-3456789
default_journal: Sales
---

# Test Client

**Address:** 123 Test Street, Test City, TC 12345
**Contact:** Test Person
**Email:** test@testclient.com
**Phone:** +1-555-0123

## Billing Information
- **Payment Terms:** Net 30
- **Tax Rate:** 10%
- **Currency:** USD
"""
        client_file.write_text(content)
        print(f"Created sample client: {client_file}")


def create_bank_transactions_file():
    """Create Bank_Transactions.md file."""
    bank_file = Path("Vault/Bank_Transactions.md")

    if not bank_file.exists():
        content = """---
last_updated: 2024-01-21T00:00:00Z
processed_count: 0
---

# Bank Transactions

## Unprocessed
<!-- New transactions will be added here -->

## Processed
<!-- Processed transactions will be moved here -->
"""
        bank_file.write_text(content)
        print(f"Created bank transactions file: {bank_file}")


def main():
    """Run all setup steps."""
    print("Setting up Odoo skills integration...\n")

    print("1. Creating Odoo environment configuration...")
    create_odoo_env()

    print("\n2. Creating Vault directory structure...")
    create_vault_structure()

    print("\n3. Creating sample client file...")
    create_sample_client()

    print("\n4. Creating bank transactions file...")
    create_bank_transactions_file()

    print("\n=== Setup Complete ===")
    print("\nNext steps:")
    print("1. Start Odoo: docker-compose -f docker-compose-odoo-simple.yml up -d")
    print("2. Wait for Odoo to initialize (2-3 minutes)")
    print("3. Open http://localhost:8069 in your browser")
    print("4. Create database with credentials:")
    print("   - Email: admin")
    print("   - Password: admin")
    print("   - Database name: odoo")
    print("5. Install Accounting app")
    print("6. Run test: python test_odoo_skills.py")


if __name__ == "__main__":
    main()