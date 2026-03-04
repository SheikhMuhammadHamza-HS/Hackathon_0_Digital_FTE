"""
Test script for Odoo skills integration.
"""

import asyncio
import logging
from ai_employee.integrations.odoo_skill_client import get_odoo_skill_client
from ai_employee.domains.invoicing.models import Invoice, Money, InvoiceLineItem, LineItemType
from decimal import Decimal
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_odoo_skills():
    """Test Odoo skills integration."""

    # Get skill client
    client = get_odoo_skill_client()

    # Test connection
    logger.info("Testing Odoo skills connection...")
    connected = await client.test_connection()
    logger.info(f"Connection test: {'PASSED' if connected else 'FAILED'}")

    # Test invoice creation
    logger.info("\nTesting invoice creation via odoo-accounting-mcp skill...")
    invoice_data = {
        "client_name": "Test Client",
        "total_amount": 1500.00,
        "due_date": "2024-02-20",
        "payment_terms": "Net 30",
        "tax_rate": 10,
        "line_items": [
            {
                "description": "Test Service",
                "quantity": 10,
                "price": 150.00,
                "unit": "hour"
            }
        ]
    }

    result = await client.create_invoice(invoice_data)
    logger.info(f"Invoice creation result: {result}")

    # Test payment creation
    logger.info("\nTesting payment creation via odoo-reconciliation skill...")
    payment_data = {
        "transaction_id": "TXN-TEST-001",
        "amount": 1500.00,
        "client_name": "Test Client",
        "invoice_reference": "INV-2024-001"
    }

    payment_result = await client.create_payment(payment_data)
    logger.info(f"Payment creation result: {payment_result}")

    logger.info("\n=== Odoo Skills Test Complete ===")


if __name__ == "__main__":
    asyncio.run(test_odoo_skills())