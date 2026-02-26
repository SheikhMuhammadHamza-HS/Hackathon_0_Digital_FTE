"""
Odoo ERP integration for AI Employee system.

Provides JSON-RPC client for Odoo Community Edition
with draft-only operations and human approval workflows.
"""

import asyncio
import logging
import json
from datetime import datetime, date
from typing import Dict, List, Optional, Any
from decimal import Decimal
import aiohttp
import xmlrpc.client
from urllib.parse import urljoin

from ..core.circuit_breaker import circuit_breaker, CircuitBreakerError
from ..core.config import get_config

logger = logging.getLogger(__name__)


class OdooClientError(Exception):
    """Base Odoo client error."""
    pass


class OdooAuthenticationError(OdooClientError):
    """Authentication error."""
    pass


class OdooConnectionError(OdooClientError):
    """Connection error."""
    pass


class OdooClient:
    """Odoo JSON-RPC client for Community Edition."""

    def __init__(self, config=None):
        """Initialize Odoo client.

        Args:
            config: Configuration object (uses global config if None)
        """
        self.config = config or get_config()
        self.session_id: Optional[str] = None
        self.user_id: Optional[int] = None
        self.company_id: Optional[int] = None

        # Connection settings
        self.base_url = self.config.odoo.url if self.config.odoo else ""
        self.database = self.config.odoo.database if self.config.odoo else ""
        self.username = self.config.odoo.username if self.config.odoo else ""
        self.password = self.config.odoo.password if self.config.odoo else ""

        # HTTP session
        self._session: Optional[aiohttp.ClientSession] = None

    async def initialize(self) -> None:
        """Initialize the client and authenticate."""
        try:
            self._session = aiohttp.ClientSession()
            await self.authenticate()
            logger.info("Odoo client initialized and authenticated")
        except Exception as e:
            logger.error(f"Failed to initialize Odoo client: {e}")
            raise

    async def shutdown(self) -> None:
        """Shutdown the client."""
        if self._session:
            await self._session.close()
            self._session = None
        logger.info("Odoo client shutdown")

    @circuit_breaker(
        name="odoo_authenticate",
        failure_threshold=3,
        recovery_timeout=60.0,
        timeout=30.0
    )
    async def authenticate(self) -> bool:
        """Authenticate with Odoo.

        Returns:
            True if authentication successful

        Raises:
            OdooAuthenticationError: If authentication fails
        """
        try:
            # Authenticate
            auth_url = urljoin(self.base_url, "/web/session/authenticate")
            auth_data = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "db": self.database,
                    "login": self.username,
                    "password": self.password
                }
            }

            async with self._session.post(auth_url, json=auth_data) as response:
                if response.status != 200:
                    raise OdooConnectionError(f"Authentication failed: HTTP {response.status}")

                result = await response.json()

                if result.get("error"):
                    raise OdooAuthenticationError(f"Authentication error: {result['error']}")

                if not result.get("result"):
                    raise OdooAuthenticationError("Invalid authentication response")

                session_info = result["result"]
                # Odoo 17 often returns session_id in cookies but sometimes also in result
                self.session_id = session_info.get("session_id") or response.cookies.get("session_id")
                if self.session_id and hasattr(self.session_id, 'value'):
                    self.session_id = self.session_id.value
                
                # If still not found, use a fallback if UID exists (session handled by aiohttp)
                if not self.session_id and session_info.get("uid"):
                    self.session_id = "ai_session"
                    
                self.user_id = session_info.get("uid")
                self.company_id = session_info.get("company_id")

                if not self.user_id:
                    raise OdooAuthenticationError("Invalid session info")

            logger.info(f"Authenticated with Odoo as user {self.user_id}")
            return True

        except Exception as e:
            logger.error(f"Odoo authentication failed: {e}")
            raise

    @circuit_breaker(
        name="odoo_create_invoice",
        failure_threshold=3,
        recovery_timeout=60.0,
        timeout=30.0
    )
    async def create_invoice(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create invoice in Odoo (draft only).

        Args:
            invoice_data: Invoice data

        Returns:
            Created invoice data

        Raises:
            OdooClientError: If creation fails
        """
        try:
            # Ensure invoice is created as draft
            invoice_data["state"] = "draft"

            # Call Odoo RPC
            result = await self._call_kw(
                "account.move",
                "create",
                [invoice_data]
            )

            invoice_id = result
            logger.info(f"Created draft invoice {invoice_id} in Odoo")

            return {"id": invoice_id, "state": "draft"}

        except Exception as e:
            logger.error(f"Failed to create invoice in Odoo: {e}")
            raise

    @circuit_breaker(
        name="odoo_post_invoice",
        failure_threshold=3,
        recovery_timeout=60.0,
        timeout=30.0
    )
    async def post_invoice(self, invoice_id: int) -> bool:
        """Post invoice (requires human approval).

        Args:
            invoice_id: Invoice ID

        Returns:
            True if posted successfully

        Raises:
            OdooClientError: If posting fails
        """
        try:
            # Check if invoice exists and is in draft state
            invoice = await self._call_kw(
                "account.move",
                "read",
                [invoice_id, ["state"]]
            )

            if not invoice:
                raise OdooClientError(f"Invoice {invoice_id} not found")

            if invoice[0]["state"] != "draft":
                raise OdooClientError(f"Invoice {invoice_id} is not in draft state")

            # Post the invoice
            await self._call_kw(
                "account.move",
                "action_post",
                [invoice_id]
            )

            logger.info(f"Posted invoice {invoice_id} in Odoo")
            return True

        except Exception as e:
            logger.error(f"Failed to post invoice {invoice_id} in Odoo: {e}")
            raise

    @circuit_breaker(
        name="odoo_create_payment",
        failure_threshold=3,
        recovery_timeout=60.0,
        timeout=30.0
    )
    async def create_payment(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create payment in Odoo (draft only).

        Args:
            payment_data: Payment data

        Returns:
            Created payment data

        Raises:
            OdooClientError: If creation fails
        """
        try:
            # Ensure payment is created as draft
            payment_data["state"] = "draft"

            # Call Odoo RPC
            result = await self._call_kw(
                "account.payment",
                "create",
                [payment_data]
            )

            payment_id = result
            logger.info(f"Created draft payment {payment_id} in Odoo")

            return {"id": payment_id, "state": "draft"}

        except Exception as e:
            logger.error(f"Failed to create payment in Odoo: {e}")
            raise

    @circuit_breaker(
        name="odoo_reconcile_payment",
        failure_threshold=3,
        recovery_timeout=60.0,
        timeout=30.0
    )
    async def reconcile_payment(self, payment_id: int) -> bool:
        """Reconcile payment (requires human approval).

        Args:
            payment_id: Payment ID

        Returns:
            True if reconciled successfully

        Raises:
            OdooClientError: If reconciliation fails
        """
        try:
            # Check if payment exists and is in draft state
            payment = await self._call_kw(
                "account.payment",
                "read",
                [payment_id, ["state"]]
            )

            if not payment:
                raise OdooClientError(f"Payment {payment_id} not found")

            if payment[0]["state"] != "draft":
                raise OdooClientError(f"Payment {payment_id} is not in draft state")

            # Reconcile the payment
            await self._call_kw(
                "account.payment",
                "action_post",
                [payment_id]
            )

            logger.info(f"Reconciled payment {payment_id} in Odoo")
            return True

        except Exception as e:
            logger.error(f"Failed to reconcile payment {payment_id} in Odoo: {e}")
            raise

    @circuit_breaker(
        name="odoo_get_open_invoices",
        failure_threshold=3,
        recovery_timeout=60.0,
        timeout=30.0
    )
    async def get_open_invoices(self) -> List[Dict[str, Any]]:
        """Get open invoices.

        Returns:
            List of open invoices

        Raises:
            OdooClientError: If query fails
        """
        try:
            # Search for open invoices
            domain = [
                ["move_type", "=", "out_invoice"],
                ["state", "in", ["posted", "sent"]],
                ["payment_state", "!=", "paid"]
            ]

            fields = [
                "id",
                "invoice_number",
                "partner_id",
                "invoice_date",
                "date_due",
                "amount_total",
                "residual",
                "state",
                "payment_state"
            ]

            invoices = await self._call_kw(
                "account.move",
                "search_read",
                [domain, fields]
            )

            # Transform results
            transformed_invoices = []
            for invoice in invoices:
                transformed_invoices.append({
                    "id": invoice["id"],
                    "invoice_number": invoice.get("invoice_number", ""),
                    "client_id": invoice["partner_id"][0] if invoice["partner_id"] else None,
                    "issue_date": invoice.get("invoice_date"),
                    "due_date": invoice.get("date_due"),
                    "amount_due": invoice.get("residual", 0.0),
                    "total_amount": invoice.get("amount_total", 0.0),
                    "status": invoice.get("state", ""),
                    "payment_status": invoice.get("payment_state", "")
                })

            logger.info(f"Retrieved {len(transformed_invoices)} open invoices from Odoo")
            return transformed_invoices

        except Exception as e:
            logger.error(f"Failed to get open invoices from Odoo: {e}")
            raise

    @circuit_breaker(
        name="odoo_get_partner",
        failure_threshold=3,
        recovery_timeout=60.0,
        timeout=30.0
    )
    async def get_partner(self, partner_id: int) -> Dict[str, Any]:
        """Get partner/customer information.

        Args:
            partner_id: Partner ID

        Returns:
            Partner data

        Raises:
            OdooClientError: If query fails
        """
        try:
            fields = [
                "id",
                "name",
                "email",
                "phone",
                "street",
                "city",
                "state_id",
                "zip",
                "country_id",
                "vat",
                "is_company"
            ]

            partner = await self._call_kw(
                "res.partner",
                "read",
                [partner_id, fields]
            )

            if not partner:
                raise OdooClientError(f"Partner {partner_id} not found")

            return partner[0]

        except Exception as e:
            logger.error(f"Failed to get partner {partner_id} from Odoo: {e}")
            raise

    async def _call_kw(self, model: str, method: str, args: List[Any], kwargs: Optional[Dict[str, Any]] = None) -> Any:
        """Call Odoo RPC method.

        Args:
            model: Model name
            method: Method name
            args: Method arguments
            kwargs: Method keyword arguments

        Returns:
            Method result

        Raises:
            OdooClientError: If RPC call fails
        """
        if not self._session or not self.session_id:
            raise OdooConnectionError("Not authenticated with Odoo")

        if kwargs is None:
            kwargs = {}

        # Prepare RPC call
        rpc_url = urljoin(self.base_url, "/web/dataset/call_kw")
        rpc_data = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": model,
                "method": method,
                "args": args,
                "kwargs": kwargs
            }
        }

        # Add session ID to context
        if "context" not in kwargs:
            kwargs["context"] = {}
        if self.session_id:
            kwargs["context"]["session_id"] = self.session_id

        try:
            async with self._session.post(rpc_url, json=rpc_data) as response:
                if response.status != 200:
                    raise OdooConnectionError(f"RPC call failed: HTTP {response.status}")

                result = await response.json()

                if result.get("error"):
                    error = result["error"]
                    raise OdooClientError(f"Odoo RPC error: {error}")

                return result.get("result")

        except aiohttp.ClientError as e:
            raise OdooConnectionError(f"Odoo connection error: {e}")

    async def test_connection(self) -> bool:
        """Test Odoo connection.

        Returns:
            True if connection is successful
        """
        try:
            # Test with a simple read operation
            result = await self._call_kw(
                "res.users",
                "search",
                [[["id", "=", 1]]]
            )

            return len(result) > 0

        except Exception as e:
            logger.error(f"Odoo connection test failed: {e}")
            return False

    async def get_server_info(self) -> Dict[str, Any]:
        """Get Odoo server information.

        Returns:
            Server information
        """
        try:
            version_info = await self._call_kw(
                "ir.module.module",
                "search_read",
                [[["name", "=", "base"], ["state", "=", "installed"]]],
                {"fields": ["name", "version", "installed_version"]}
            )

            if version_info:
                base_module = version_info[0]
                return {
                    "version": base_module.get("installed_version"),
                    "series": base_module.get("version"),
                    "database": self.database,
                    "server_url": self.base_url
                }

            return {}

        except Exception as e:
            logger.error(f"Failed to get Odoo server info: {e}")
            return {}


# Global Odoo client instance
odoo_client = OdooClient()


def get_odoo_client() -> OdooClient:
    """Get the global Odoo client instance.

    Returns:
        Global Odoo client
    """
    return odoo_client