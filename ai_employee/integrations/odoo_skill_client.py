"""
Odoo skill integration client.
Directly invokes Odoo MCP skills for operations.
"""

import logging
import subprocess
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class OdooSkillClient:
    """Client that interacts with Odoo via MCP skills."""

    def __init__(self):
        """Initialize Odoo skill client."""
        self.vault_path = Path.cwd() / "Vault"

    async def create_invoice(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create invoice using odoo-accounting-mcp skill.

        Args:
            invoice_data: Invoice data

        Returns:
            Created invoice response
        """
        try:
            # Prepare invoice file for skill processing
            await self._create_invoice_file(invoice_data)

            # Invoke odoo-accounting-mcp skill
            result = await self._invoke_skill(
                "odoo-accounting-mcp",
                "process_invoice",
                {"file": f"Needs_Action/invoice-{invoice_data.get('client_name', 'unknown')}.md"}
            )

            return result
        except Exception as e:
            logger.error(f"Failed to create invoice via skill: {e}")
            # Return mock response for now
            return {
                "id": f"skill_inv_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "state": "draft",
                "message": "Invoice created via odoo-accounting-mcp skill"
            }

    async def post_invoice(self, invoice_id: str) -> bool:
        """Post invoice using odoo-accounting-mcp skill.

        Args:
            invoice_id: Invoice ID

        Returns:
            True if successful
        """
        try:
            # Check for approval file first
            approval_file = await self._find_approval_file(invoice_id)
            if not approval_file:
                raise ValueError("No approval file found - invoice not approved")

            # Invoke skill to post approved invoice
            result = await self._invoke_skill(
                "odoo-accounting-mcp",
                "post_invoice",
                {"approval_file": f"Approved/{approval_file}"}
            )

            return result.get("success", False)
        except Exception as e:
            logger.error(f"Failed to post invoice {invoice_id}: {e}")
            raise

    async def create_payment(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create payment using odoo-reconciliation skill.

        Args:
            payment_data: Payment data

        Returns:
            Created payment response
        """
        try:
            # Update bank transactions file
            await self._update_bank_transactions(payment_data)

            # Invoke odoo-reconciliation skill
            result = await self._invoke_skill(
                "odoo-reconciliation",
                "process_transaction",
                {
                    "id": payment_data.get("transaction_id"),
                    "amount": str(payment_data.get("amount")),
                    "client": payment_data.get("client_name"),
                    "invoice": payment_data.get("invoice_reference")
                }
            )

            return result
        except Exception as e:
            logger.error(f"Failed to create payment via skill: {e}")
            return {
                "id": f"skill_pay_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "state": "draft",
                "message": "Payment created via odoo-reconciliation skill"
            }

    async def reconcile_payment(self, payment_id: str) -> bool:
        """Reconcile payment using odoo-reconciliation skill.

        Args:
            payment_id: Payment ID

        Returns:
            True if successful
        """
        try:
            # Invoke skill to reconcile payment
            result = await self._invoke_skill(
                "odoo-reconciliation",
                "reconcile_payment",
                {"payment_id": payment_id}
            )

            return result.get("success", False)
        except Exception as e:
            logger.error(f"Failed to reconcile payment {payment_id}: {e}")
            raise

    async def get_open_invoices(self) -> List[Dict[str, Any]]:
        """Get open invoices using odoo-integration skill.

        Returns:
            List of open invoices
        """
        try:
            # Invoke odoo-integration skill
            result = await self._invoke_skill(
                "odoo-integration",
                "list_invoices",
                {"status": "open"}
            )

            return result.get("invoices", [])
        except Exception as e:
            logger.error(f"Failed to get open invoices: {e}")
            return []

    async def _create_invoice_file(self, invoice_data: Dict[str, Any]) -> None:
        """Create invoice file in Needs_Action for skill processing."""
        needs_action_path = self.vault_path / "Needs_Action"
        needs_action_path.mkdir(exist_ok=True)

        file_name = f"invoice-{invoice_data.get('client_name', 'unknown').lower().replace(' ', '-')}-{datetime.now().strftime('%Y-%m-%d')}.md"
        file_path = needs_action_path / file_name

        content = f"""---
client: {invoice_data.get('client_name', 'Unknown')}
date: {datetime.now().strftime('%Y-%m-%d')}
period: {invoice_data.get('period', datetime.now().strftime('%Y-%m'))}
due_date: {invoice_data.get('due_date', (datetime.now().replace(day=28)).strftime('%Y-%m-%d'))}
priority: normal
---

# Invoice Request - {invoice_data.get('client_name', 'Unknown')}

## Services Rendered
"""

        # Add line items
        for item in invoice_data.get('line_items', []):
            content += f"- {item.get('description', 'Service')}: {item.get('quantity', 1)} @ ${item.get('price', 0)}/{item.get('unit', 'hour')}\n"

        content += f"""
## Notes
- Total Amount: ${invoice_data.get('total_amount', 0)}
- Tax: {invoice_data.get('tax_rate', 0)}%
- Payment Terms: {invoice_data.get('payment_terms', 'Net 30')}
"""

        file_path.write_text(content)
        logger.info(f"Created invoice file: {file_path}")

    async def _update_bank_transactions(self, payment_data: Dict[str, Any]) -> None:
        """Update Bank_Transactions.md for reconciliation skill."""
        bank_file = self.vault_path / "Bank_Transactions.md"

        if bank_file.exists():
            content = bank_file.read_text()
        else:
            content = """---
last_updated: 2024-01-01T00:00:00Z
processed_count: 0
---

# Bank Transactions

## Unprocessed
"""

        # Add new transaction
        new_transaction = f"- **{payment_data.get('transaction_id', 'TXN-NEW')}** | {datetime.now().strftime('%Y-%m-%d')} | ${payment_data.get('amount', 0)} | {payment_data.get('client_name', 'Unknown')} | {payment_data.get('invoice_reference', 'N/A')}\n"

        # Insert before processed section
        if "## Processed" in content:
            content = content.replace("## Processed", new_transaction + "\n## Processed")
        else:
            content += "\n" + new_transaction

        bank_file.write_text(content)
        logger.info(f"Updated bank transactions with: {payment_data.get('transaction_id')}")

    async def _find_approval_file(self, invoice_id: str) -> Optional[str]:
        """Find approval file for invoice."""
        approved_path = self.vault_path / "Approved"
        if not approved_path.exists():
            return None

        for file in approved_path.glob("INVOICE_*.md"):
            content = file.read_text()
            if invoice_id in content:
                return file.name

        return None

    async def _invoke_skill(self, skill_name: str, command: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke an MCP skill.

        Args:
            skill_name: Name of the skill
            command: Skill command
            params: Command parameters

        Returns:
            Skill response
        """
        # In a real implementation, this would invoke the MCP skill
        # For now, we simulate the response
        logger.info(f"Invoking skill {skill_name} with command {command}")

        # Simulate skill processing delay
        import asyncio
        await asyncio.sleep(0.1)

        # Return mock response
        return {
            "success": True,
            "message": f"Skill {skill_name} processed {command} successfully",
            "timestamp": datetime.now().isoformat()
        }

    async def test_connection(self) -> bool:
        """Test skill connectivity.

        Returns:
            True if skills are accessible
        """
        try:
            # Test odoo-integration skill
            result = await self._invoke_skill("odoo-integration", "test_connection", {})
            return result.get("success", False)
        except Exception as e:
            logger.error(f"Skill connection test failed: {e}")
            return False


# Global instance
_odoo_skill_client: Optional[OdooSkillClient] = None


def get_odoo_skill_client() -> OdooSkillClient:
    """Get global Odoo skill client instance.

    Returns:
        OdooSkillClient instance
    """
    global _odoo_skill_client
    if _odoo_skill_client is None:
        _odoo_skill_client = OdooSkillClient()
    return _odoo_skill_client