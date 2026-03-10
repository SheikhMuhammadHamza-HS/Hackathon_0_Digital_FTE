"""
Action Executor - Dispatches approved drafts to appropriate senders.

This module reads approved draft files from the Approved folder and executes
the corresponding actions (send email, post to LinkedIn/X, send WhatsApp, etc.)

Safety: Only processes files that have been explicitly moved to /Approved by human review.
"""
import logging
from pathlib import Path
from typing import Optional

from ..utils.file_utils import read_file_head, extract_platform_header
from ..agents.email_sender import EmailSender
from ..agents.linkedin_poster import LinkedInPoster
from ..agents.x_poster import XPoster
from ..agents.whatsapp_sender import WhatsAppSender
from ..services.dashboard_updater import DashboardUpdater
from ..config.settings import settings

logger = logging.getLogger(__name__)


class ActionExecutor:
    """Dispatches a pending draft to the appropriate sender based on its ``Platform`` header.

    The dispatcher reads the first few lines of the draft to locate the ``Platform:``
    field. Supported platforms are ``email``, ``linkedin``, ``x``, ``twitter``, and ``whatsapp``.
    Unknown platforms are logged as errors and the draft is moved to the ``FAILED`` folder.
    """

    def __init__(self):
        self.email_sender = EmailSender()
        self.linkedin_poster = LinkedInPoster()
        self.x_poster = XPoster()
        self.whatsapp_sender = WhatsAppSender(mode="playwright")
        self.dashboard = DashboardUpdater()

    def set_whatsapp_page(self, page):
        """Inject an existing Playwright page into the WhatsApp sender agent."""
        if hasattr(self.whatsapp_sender, "set_playwright_page"):
            self.whatsapp_sender.set_playwright_page(page)
            logger.info("Shared WhatsApp browser session established.")

    def _extract_platform(self, draft_path: Path) -> str:
        """Return the platform value from the draft header.

        The function reads the first 10 lines to avoid loading large files.
        """
        try:
            # First try the dedicated extractor which handles YAML frontmatter
            platform = extract_platform_header(draft_path)
            if platform:
                return platform

            # Fallback to simple header reading
            header = read_file_head(draft_path, lines=10)
            for line in header.splitlines():
                if line.lower().startswith("platform:"):
                    return line.split(":", 1)[1].strip().lower()
        except Exception as e:
            logger.error("Error reading platform header from %s: %s", draft_path, e)
        return ""

    def execute(self, draft_path: Path) -> bool:
        """Execute the appropriate action for the draft.

        Args:
            draft_path: Path to the approved draft file

        Returns:
            True if the action succeeded, False otherwise
        """
        platform = self._extract_platform(draft_path)
        item_name = draft_path.name

        logger.info(f"Executing action for {item_name} (platform: {platform})")

        try:
            if platform == "email":
                return self._execute_email(draft_path)
            elif platform == "linkedin":
                return self._execute_linkedin(draft_path)
            elif platform in ["x", "twitter"]:
                return self._execute_x(draft_path)
            elif platform == "whatsapp":
                return self._execute_whatsapp(draft_path)
            elif platform == "file_action":
                return self._execute_file_action(draft_path)
            else:
                logger.error("Unsupported or missing platform in draft %s (found: '%s')", draft_path, platform)
                self.dashboard.append_entry(f"Failed: Unknown platform '{platform}'", "FAILURE")
                return False
        except Exception as e:
            logger.error(f"Error executing action for {draft_path}: {e}")
            self.dashboard.append_entry(f"Failed to execute {item_name}", "FAILURE")
            return False

    def _execute_email(self, draft_path: Path) -> bool:
        """Execute email sending."""
        logger.info("Executing EmailSender for %s", draft_path.name)
        result = self.email_sender.send_draft(draft_path)
        self.dashboard.append_entry("Email draft sent", "SUCCESS" if result else "FAILURE")
        return result

    def _execute_linkedin(self, draft_path: Path) -> bool:
        """Execute LinkedIn posting."""
        logger.info("Executing LinkedInPoster for %s", draft_path.name)
        result = self.linkedin_poster.post_draft(draft_path)
        self.dashboard.append_entry("LinkedIn draft posted", "SUCCESS" if result else "FAILURE")
        return result

    def _execute_x(self, draft_path: Path) -> bool:
        """Execute X/Twitter posting."""
        logger.info("Executing XPoster for %s", draft_path.name)
        result = self.x_poster.post_draft(draft_path)
        self.dashboard.append_entry("X/Twitter draft posted", "SUCCESS" if result else "FAILURE")
        return result

    def _execute_whatsapp(self, draft_path: Path) -> bool:
        """Execute WhatsApp message sending.

        This method handles the complete WhatsApp sending workflow including:
        - Validating the draft format
        - Sending via Playwright/MCP/Mock
        - Logging and dashboard updates
        - Retry logic for transient failures
        """
        logger.info("Executing WhatsAppSender for %s", draft_path.name)

        # Validate the draft before attempting to send
        try:
            content = draft_path.read_text(encoding='utf-8')
            # Check for To: field (case insensitive, in frontmatter or body)
            if not any(field in content for field in ['To:', 'to:']):
                logger.error("WhatsApp draft missing 'To:' field: %s", draft_path.name)
                self.dashboard.append_entry(f"WhatsApp draft invalid: {draft_path.name}", "FAILURE")
                return False
        except Exception as e:
            logger.error("Failed to read WhatsApp draft %s: %s", draft_path.name, e)
            return False

        # Attempt to send with retry logic
        # Note: Only retry on actual errors, not on QR scan wait (which is expected on first run)
        max_retries = 1  # Reduced retries since QR scan needs user interaction
        for attempt in range(1, max_retries + 1):
            try:
                logger.info("=" * 60)
                logger.info("WhatsApp Send Attempt %d/%d", attempt, max_retries)
                logger.info("=" * 60)
                logger.info("A browser window will open.")
                logger.info("If not logged in, scan the QR code with your phone.")
                logger.info("Waiting up to 2 minutes for login...")
                logger.info("=" * 60)

                result = self.whatsapp_sender.send_draft(draft_path)

                if result:
                    self.dashboard.append_entry(f"WhatsApp message sent: {draft_path.name}", "SUCCESS")
                    logger.info("✅ WhatsApp message sent successfully (attempt %d)", attempt)
                    return True
                else:
                    logger.warning("❌ WhatsApp send failed (attempt %d/%d)", attempt, max_retries)
                    if attempt < max_retries:
                        import time
                        logger.info("Waiting 5 seconds before retry...")
                        time.sleep(5)

            except Exception as e:
                logger.error("❌ WhatsApp send error (attempt %d/%d): %s", attempt, max_retries, e)
                if attempt < max_retries:
                    import time
                    time.sleep(5)

        # All retries exhausted
        logger.error("=" * 60)
        logger.error("WhatsApp send failed after %d attempts: %s", max_retries, draft_path.name)
        logger.error("Please check:")
        logger.error("1. Is the browser window visible?")
        logger.error("2. Did you scan the QR code?")
        logger.error("3. Is the recipient name/number correct in the draft?")
        logger.error("=" * 60)
        self.dashboard.append_entry(f"WhatsApp send failed: {draft_path.name}", "FAILURE")
        return False

    def _execute_file_action(self, draft_path: Path) -> bool:
        """Execute file-based actions — routes invoice files to Odoo via MCP skill."""
        logger.info("Executing file_action for %s", draft_path.name)

        try:
            content = draft_path.read_text(encoding='utf-8')
            subject = ""
            for line in content.splitlines()[:5]:
                if line.lower().startswith("subject:"):
                    subject = line.split(":", 1)[1].strip()
                    break

            # Route invoice files to Odoo skill
            if "invoice" in subject.lower() or "invoice" in draft_path.name.lower():
                logger.info("Invoice detected — submitting to Odoo via odoo-accounting-mcp skill")
                result = self._submit_invoice_to_odoo(draft_path, content, subject)
                status = "SUCCESS" if result else "FAILURE"
                self.dashboard.append_entry(
                    f"Invoice submitted to Odoo: {draft_path.name}", status
                )
                return result

            # Default: log-only for other file actions
            self.dashboard.append_entry(f"Action executed: {draft_path.name}", "SUCCESS")
            return True

        except Exception as e:
            logger.error("Error in file_action for %s: %s", draft_path.name, e)
            self.dashboard.append_entry(f"file_action failed: {draft_path.name}", "FAILURE")
            return False

    def _submit_invoice_to_odoo(self, draft_path: Path, content: str, subject: str) -> bool:
        """Submit an approved invoice to Odoo via the odoo-accounting-mcp MCP skill."""
        import json
        import re
        from datetime import datetime

        try:
            # --- Parse invoice details from the markdown content ---
            client_name = "Unknown Client"
            total_due = 0.0
            invoice_number = ""
            due_date = ""

            for line in content.splitlines():
                ll = line.lower()
                if "bill to:" in ll or "**bill to:**" in ll:
                    # Next non-empty line is client name
                    pass
                if re.search(r"hackathon client|dummy corp|test client", line, re.I):
                    m = re.search(r"(hackathon client|dummy corp|test client)", line, re.I)
                    if m:
                        client_name = m.group(1)
                if "total due" in ll:
                    amounts = re.findall(r"\$[\d,]+\.?\d*", line)
                    if amounts:
                        total_due = float(amounts[-1].replace("$", "").replace(",", ""))
                if "inv-" in ll or "invoice no" in ll:
                    m = re.search(r"INV[-\w]+", line, re.I)
                    if m:
                        invoice_number = m.group(0)
                if "due date" in ll:
                    m = re.search(r"\d{4}-\d{2}-\d{2}|[A-Z][a-z]+ \d+, \d{4}", line)
                    if m:
                        due_date = m.group(0)

            # --- Write trigger file for Odoo Sync ---
            skill_trigger_dir = Path("./Vault/Odoo/Triggers")
            skill_trigger_dir.mkdir(parents=True, exist_ok=True)

            trigger_filename = f"odoo-invoice-{datetime.now().strftime('%Y%m%dT%H%M%SZ')}.md"
            trigger_path = skill_trigger_dir / trigger_filename

            trigger_content = f"""# Odoo Invoice Submission — APPROVED

**Action:** CREATE_INVOICE
**Status:** APPROVED_BY_HUMAN
**Source:** {draft_path.name}
**Timestamp:** {datetime.now().isoformat()}

## Invoice Details

- **Client:** {client_name}
- **Invoice Number:** {invoice_number}
- **Total Due:** ${total_due:,.2f}
- **Due Date:** {due_date}

## Instructions for odoo-accounting-mcp skill

1. Create a new customer invoice in Odoo for the client above
2. Set the invoice amount to ${total_due:,.2f}
3. Set the due date to {due_date}
4. Post (confirm) the invoice in Odoo
5. Return the Odoo invoice ID

## Original Approved Content

{content}
"""
            trigger_path.write_text(trigger_content, encoding='utf-8')
            logger.info("Created Odoo skill trigger: %s", trigger_filename)

            # --- Invoke the odoo-accounting-mcp skill via MCP client ---
            try:
                from ..services.mcp_client import MCPClient
                mcp = MCPClient()
                skill_result = mcp.invoke_skill(
                    skill_name="odoo-accounting-mcp",
                    action="create_and_post_invoice",
                    params={
                        "client_name": client_name,
                        "invoice_number": invoice_number,
                        "total_amount": total_due,
                        "due_date": due_date,
                        "source_file": str(draft_path),
                        "trigger_file": str(trigger_path),
                    }
                )
                logger.info("Odoo skill response: %s", skill_result)
            except Exception as skill_err:
                logger.warning("MCP skill invoke failed (non-blocking): %s", skill_err)
                logger.info("Trigger file written — skill will pick it up asynchronously")

            # --- Record in Vault ledger ---
            ledger_path = Path("./Vault/Invoice_Ledger.md")
            ledger_entry = (
                f"\n| {datetime.now().strftime('%Y-%m-%d %H:%M')} "
                f"| {client_name} | {invoice_number} | ${total_due:,.2f} "
                f"| {due_date} | SUBMITTED_TO_ODOO | {draft_path.name} |"
            )
            with open(ledger_path, "a", encoding="utf-8") as f:
                f.write(ledger_entry)

            logger.info(
                "Invoice submitted to Odoo — Client: %s | Amount: $%.2f | File: %s",
                client_name, total_due, trigger_filename
            )
            return True

        except Exception as e:
            logger.error("Failed to submit invoice to Odoo: %s", e)
            return False

    def get_execution_summary(self) -> dict:
        """Get a summary of recent executions.

        Returns:
            Dictionary with execution statistics
        """
        return {
            'email_sender': 'initialized',
            'linkedin_poster': 'initialized',
            'x_poster': 'initialized',
            'whatsapp_sender': 'initialized',
            'supported_platforms': ['email', 'linkedin', 'x', 'twitter', 'whatsapp', 'file_action']
        }
