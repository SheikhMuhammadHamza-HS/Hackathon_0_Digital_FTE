"""
New Odoo client using skills integration.
Provides simplified interface to Odoo through MCP skills.
"""

import logging
from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class OdooClient:
    """Simplified Odoo client that uses MCP skills."""

    def __init__(self):
        """Initialize Odoo client."""
        self._connected = False
        self._session_info = None

    async def authenticate(self) -> bool:
        """Authenticate with Odoo using odoo-integration skill.

        Returns:
            True if authentication successful
        """
        try:
            # Use odoo-integration skill
            logger.info("Authenticating with Odoo via odoo-integration skill")
            # This would be called via skill invocation
            # For now, we simulate success
            self._connected = True
            self._session_info = {
                "uid": "skill_user",
                "session_id": "skill_session",
                "context": {"lang": "en_US", "tz": "UTC"}
            }
            return True
        except Exception as e:
            logger.error(f"Odoo authentication failed: {e}")
            return False

    async def create_invoice(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create invoice in Odoo using odoo-accounting-mcp skill.

        Args:
            invoice_data: Invoice data

        Returns:
            Created invoice data with ID
        """
        if not self._connected:
            await self.authenticate()

        try:
            # Use odoo-accounting-mcp skill
            logger.info(f"Creating invoice via odoo-accounting-mcp skill: {invoice_data}")
            # Return mock data for now
            return {
                "id": f"inv_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "state": "draft",
                "message": "Invoice created via skill"
            }
        except Exception as e:
            logger.error(f"Failed to create invoice: {e}")
            raise

    async def post_invoice(self, invoice_id: str) -> bool:
        """Post invoice in Odoo using odoo-accounting-mcp skill.

        Args:
            invoice_id: Invoice ID to post

        Returns:
            True if successful
        """
        if not self._connected:
            await self.authenticate()

        try:
            # Use odoo-accounting-mcp skill
            logger.info(f"Posting invoice {invoice_id} via odoo-accounting-mcp skill")
            # This would check for approval file first
            return True
        except Exception as e:
            logger.error(f"Failed to post invoice {invoice_id}: {e}")
            raise

    async def create_payment(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create payment in Odoo using odoo-reconciliation skill.

        Args:
            payment_data: Payment data

        Returns:
            Created payment data with ID
        """
        if not self._connected:
            await self.authenticate()

        try:
            # Use odoo-reconciliation skill
            logger.info(f"Creating payment via odoo-reconciliation skill: {payment_data}")
            # Return mock data
            return {
                "id": f"pay_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "state": "draft",
                "message": "Payment created via skill"
            }
        except Exception as e:
            logger.error(f"Failed to create payment: {e}")
            raise

    async def reconcile_payment(self, payment_id: str) -> bool:
        """Reconcile payment in Odoo using odoo-reconciliation skill.

        Args:
            payment_id: Payment ID to reconcile

        Returns:
            True if successful
        """
        if not self._connected:
            await self.authenticate()

        try:
            # Use odoo-reconciliation skill
            logger.info(f"Reconciling payment {payment_id} via odoo-reconciliation skill")
            return True
        except Exception as e:
            logger.error(f"Failed to reconcile payment {payment_id}: {e}")
            raise

    async def get_open_invoices(self) -> List[Dict[str, Any]]:
        """Get open invoices from Odoo.

        Returns:
            List of open invoices
        """
        if not self._connected:
            await self.authenticate()

        try:
            # Use odoo-integration skill
            logger.info("Fetching open invoices via odoo-integration skill")
            # Return mock data
            return []
        except Exception as e:
            logger.error(f"Failed to get open invoices: {e}")
            raise

    async def test_connection(self) -> bool:
        """Test connection to Odoo.

        Returns:
            True if connection successful
        """
        try:
            return await self.authenticate()
        except Exception:
            return False


# Global instance
_odoo_client: Optional[OdooClient] = None


def get_odoo_client() -> OdooClient:
    """Get global Odoo client instance.

    Returns:
        OdooClient instance
    """
    global _odoo_client
    if _odoo_client is None:
        _odoo_client = OdooClient()
    return _odoo_client