"""
Email service integration for AI Employee system.

Provides email sending capabilities with multiple providers
and template management.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.application import MIMEApplication
from email.utils import formataddr
import base64

from ..core.circuit_breaker import circuit_breaker, CircuitBreakerError
from ..core.config import get_config

logger = logging.getLogger(__name__)


class EmailServiceError(Exception):
    """Base email service error."""
    pass


class EmailConfigurationError(EmailServiceError):
    """Email configuration error."""
    pass


class EmailService:
    """Email service with multiple provider support."""

    def __init__(self, config=None):
        """Initialize email service.

        Args:
            config: Configuration object (uses global config if None)
        """
        self.config = config or get_config()
        self.email_config = self.config.email

    def _get_smtp_config(self) -> Dict[str, Any]:
        """Get SMTP configuration.

        Returns:
            SMTP configuration

        Raises:
            EmailConfigurationError: If configuration is invalid
        """
        if not self.email_config:
            raise EmailConfigurationError("Email configuration not found")

        required_fields = ["host", "user", "password"]
        for field in required_fields:
            if not getattr(self.email_config, field):
                raise EmailConfigurationError(f"Missing required email config: {field}")

        return {
            "host": self.email_config.host,
            "port": self.email_config.port,
            "user": self.email_config.user,
            "password": self.email_config.password,
            "use_tls": self.email_config.use_tls,
            "timeout": self.email_config.timeout,
            "from_email": self.email_config.from_email
        }

    @circuit_breaker(
        name="email_send",
        failure_threshold=3,
        recovery_timeout=60.0,
        timeout=30.0
    )
    async def send_email(
        self,
        to_email: Union[str, List[str]],
        subject: str,
        body: str,
        cc: Optional[Union[str, List[str]]] = None,
        bcc: Optional[Union[str, List[str]]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        html_body: Optional[str] = None
    ) -> bool:
        """Send email.

        Args:
            to_email: Recipient email(s)
            subject: Email subject
            body: Email body (plain text)
            cc: CC recipient(s)
            bcc: BCC recipient(s)
            attachments: List of attachments
            html_body: HTML email body

        Returns:
            True if sent successfully

        Raises:
            EmailServiceError: If sending fails
        """
        try:
            smtp_config = self._get_smtp_config()

            # Create message
            message = self._create_message(
                to_email=to_email,
                subject=subject,
                body=body,
                html_body=html_body,
                cc=cc,
                bcc=bcc,
                attachments=attachments,
                from_email=smtp_config["from_email"]
            )

            # Send email
            await self._send_smtp(message, smtp_config)

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            raise EmailServiceError(f"Email sending failed: {e}")

    async def send_invoice(self, to_email: str, subject: str, body: str, invoice_id: str) -> bool:
        """Send invoice email.

        Args:
            to_email: Recipient email
            subject: Email subject
            body: Email body
            invoice_id: Invoice ID

        Returns:
            True if sent successfully
        """
        try:
            # Add invoice tracking to body
            tracked_body = f"{body}\n\n---\nInvoice ID: {invoice_id}\nSent: {datetime.utcnow().isoformat()}"

            return await self.send_email(
                to_email=to_email,
                subject=subject,
                body=tracked_body
            )

        except Exception as e:
            logger.error(f"Failed to send invoice email: {e}")
            raise

    async def send_notification(
        self,
        to_email: str,
        subject: str,
        message: str,
        priority: str = "normal"
    ) -> bool:
        """Send notification email.

        Args:
            to_email: Recipient email
            subject: Email subject
            message: Notification message
            priority: Priority level (low, normal, high)

        Returns:
            True if sent successfully
        """
        try:
            # Add priority prefix to subject if needed
            if priority == "high":
                subject = f"[HIGH PRIORITY] {subject}"
            elif priority == "low":
                subject = f"[INFO] {subject}"

            return await self.send_email(
                to_email=to_email,
                subject=subject,
                body=message
            )

        except Exception as e:
            logger.error(f"Failed to send notification email: {e}")
            raise

    def _create_message(
        self,
        to_email: Union[str, List[str]],
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        cc: Optional[Union[str, List[str]]] = None,
        bcc: Optional[Union[str, List[str]]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        from_email: str = "AI Employee <noreply@company.com>"
    ) -> MIMEMultipart:
        """Create email message.

        Args:
            to_email: Recipient email(s)
            subject: Email subject
            body: Email body
            html_body: HTML email body
            cc: CC recipient(s)
            bcc: BCC recipient(s)
            attachments: List of attachments
            from_email: From email address

        Returns:
            Email message
        """
        # Create message
        message = MIMEMultipart("mixed")
        message["Subject"] = subject
        message["From"] = from_email
        message["To"] = self._format_email_addresses(to_email)

        if cc:
            message["Cc"] = self._format_email_addresses(cc)

        if bcc:
            message["Bcc"] = self._format_email_addresses(bcc)

        # Create alternative part for plain text and HTML
        alternative = MIMEMultipart("alternative")

        # Plain text part
        text_part = MIMEText(body, "plain", _charset="utf-8")
        alternative.attach(text_part)

        # HTML part if provided
        if html_body:
            html_part = MIMEText(html_body, "html", _charset="utf-8")
            alternative.attach(html_part)

        message.attach(alternative)

        # Add attachments
        if attachments:
            for attachment in attachments:
                part = self._create_attachment_part(attachment)
                message.attach(part)

        return message

    def _format_email_addresses(self, addresses: Union[str, List[str]]) -> str:
        """Format email addresses.

        Args:
            addresses: Email address(es)

        Returns:
            Formatted address string
        """
        if isinstance(addresses, str):
            addresses = [addresses]

        formatted = []
        for addr in addresses:
            if "@" in addr and "<" in addr and ">" in addr:
                # Already formatted
                formatted.append(addr)
            else:
                # Format as "Name <email>"
                formatted.append(formataddr(("", addr))

        return ", ".join(formatted)

    def _create_attachment_part(self, attachment: Dict[str, Any]) -> Union[MIMEBase, MIMEApplication]:
        """Create attachment part.

        Args:
            attachment: Attachment data

        Returns:
            Attachment part
        """
        filename = attachment.get("filename", "attachment")
        content = attachment.get("content", "")
        content_type = attachment.get("content_type", "application/octet-stream")

        if content_type.startswith("text/"):
            # Text file
            part = MIMEText(content, content_type.split("/")[-1], _charset="utf-8")
        else:
            # Binary file
            part = MIMEApplication(content.encode("utf-8"))
            part.add_header("Content-Disposition", f"attachment; filename={filename}")

        part.add_header("Content-Type", content_type)
        return part

    async def _send_smtp(self, message: MIMEMultipart, smtp_config: Dict[str, Any]) -> None:
        """Send email via SMTP.

        Args:
            message: Email message
            smtp_config: SMTP configuration

        Raises:
            EmailServiceError: If SMTP sending fails
        """
        try:
            # Connect to SMTP server
            smtp = smtplib.SMTP(
                host=smtp_config["host"],
                port=smtp_config["port"],
                timeout=smtp_config["timeout"]
            )

            # Start TLS if required
            if smtp_config["use_tls"]:
                smtp.starttls()

            # Login
            smtp.login(smtp_config["user"], smtp_config["password"])

            # Send message
            smtp.send_message(message)

            # Quit
            smtp.quit()

        except smtplib.SMTPException as e:
            raise EmailServiceError(f"SMTP error: {e}")
        except Exception as e:
            raise EmailServiceError(f"Email sending error: {e}")

    async def test_connection(self) -> bool:
        """Test email service connection.

        Returns:
            True if connection is successful
        """
        try:
            smtp_config = self._get_smtp_config()

            # Try to connect and authenticate
            smtp = smtplib.SMTP(
                host=smtp_config["host"],
                port=smtp_config["port"],
                timeout=smtp_config["timeout"]
            )

            if smtp_config["use_tls"]:
                smtp.starttls()

            smtp.login(smtp_config["user"], smtp_config["password"])
            smtp.quit()

            logger.info("Email service connection test successful")
            return True

        except Exception as e:
            logger.error(f"Email service connection test failed: {e}")
            return False

    async def get_email_templates(self) -> Dict[str, str]:
        """Get available email templates.

        Returns:
            Dictionary of templates
        """
        templates = {
            "invoice": """
Subject: Invoice {invoice_number}

Dear {client_name},

Please find your invoice {invoice_number} attached.

Amount Due: {amount}
Due Date: {due_date}

Payment Terms: {terms}

Best regards,
AI Employee System
            """.strip(),
            "payment_received": """
Subject: Payment Received - Thank You!

Dear {client_name},

We've received your payment of {amount} for invoice {invoice_number}.

Payment Details:
- Amount: {amount}
- Date: {payment_date}
- Reference: {reference}

Thank you for your business!

Best regards,
AI Employee System
            """.strip(),
            "approval_required": """
Subject: Approval Required - {item_type}

Hello,

A {item_type} requires your approval:

Item: {item_id}
Amount: ${amount}
Reason: {reason}

Please review and approve or reject this request.

Best regards,
AI Employee System
            """.strip()
        }

        return templates

    def render_template(self, template_name: str, **kwargs) -> str:
        """Render email template with variables.

        Args:
            template_name: Template name
            **kwargs: Template variables

        Returns:
            Rendered template
        """
        templates = asyncio.run(self.get_email_templates())

        if template_name not in templates:
            raise EmailServiceError(f"Template '{template_name}' not found")

        template = templates[template_name]

        # Replace placeholders
        for key, value in kwargs.items():
            placeholder = "{" + key + "}"
            template = template.replace(placeholder, str(value))

        return template

    async def send_template_email(
        self,
        template_name: str,
        to_email: str,
        **template_vars
    ) -> bool:
        """Send email using template.

        Args:
            template_name: Template name
            to_email: Recipient email
            **template_vars: Template variables

        Returns:
            True if sent successfully
        """
        try:
            # Render template
            body = self.render_template(template_name, **template_vars)

            # Extract subject from first line
            lines = body.split('\n')
            subject = lines[0].replace("Subject: ", "").strip()
            body = '\n'.join(lines[2:]).strip()

            # Add default subject if not found
            if not subject:
                subject = f"Notification from AI Employee System"

            return await self.send_email(
                to_email=to_email,
                subject=subject,
                body=body
            )

        except Exception as e:
            logger.error(f"Failed to send template email '{template_name}': {e}")
            raise


# Global email service instance
email_service = EmailService()


def get_email_service() -> EmailService:
    """Get the global email service instance.

    Returns:
        Global email service
    """
    return email_service