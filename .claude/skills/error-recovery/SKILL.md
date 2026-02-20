---
name: error-recovery
description: Handle API failures gracefully with exponential backoff, error categorization, and intelligent retry logic. Implements hackathon guide Section 7 error recovery strategies. Use when Claude needs to: (1) Retry transient failures with backoff, (2) Categorize and log errors appropriately, (3) Queue failed actions for manual review, (4) Handle service outages gracefully, (5) Never auto-retry payment operations
license: Complete terms in LICENSE.txt
---

# Error Recovery

This skill provides comprehensive error handling and recovery mechanisms following the hackathon guide Section 7 specifications, with exponential backoff, error categorization, and strict rules for payment operations.

## Prerequisites

### Environment Configuration
Required `.env` variables:
```bash
MAX_RETRY_ATTEMPTS=3
BASE_RETRY_DELAY=1
MAX_RETRY_DELAY=60
PAYMENT_RETRY=false  # NEVER change to true
ERROR_LOG_PATH=/Logs/errors
TEMP_QUEUE_PATH=/tmp/operation_queue
```

## Error Categories & Recovery Strategies

### Transient Errors
**Examples:**
- Network timeout
- Rate limit exceeded
- Temporary service unavailable
- Connection refused

**Recovery Strategy:**
- Exponential backoff retry
- Continue until max attempts
- Log each retry attempt

### Authentication Errors
**Examples:**
- Expired token
- Revoked access
- Invalid credentials
- Permission denied

**Recovery Strategy:**
- Alert human immediately
- Pause all operations
- Require manual credential refresh

### Logic Errors
**Examples:**
- Claude misinterprets message
- Invalid command parameters
- Workflow logic failure

**Recovery Strategy:**
- Add to human review queue
- Continue with other operations
- Detailed error logging

### Data Errors
**Examples:**
- Corrupted file
- Missing required field
- Invalid data format
- File permission issues

**Recovery Strategy:**
- Quarantine problematic data
- Alert human with specifics
- Skip but continue processing

### System Errors
**Examples:**
- Orchestrator crash
- Disk full
- Memory exhausted
- Service unavailable

**Recovery Strategy:**
- Watchdog auto-restart
- System health check
- Emergency mode activation

## Implementation Details

### Error Handler Class

```python
import time
import json
import logging
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, Callable

class ErrorCategory(Enum):
    TRANSIENT = "transient"
    AUTH = "auth"
    LOGIC = "logic"
    DATA = "data"
    SYSTEM = "system"

class ErrorRecoveryHandler:
    def __init__(self):
        self.max_attempts = int(os.getenv('MAX_RETRY_ATTEMPTS', 3))
        self.base_delay = int(os.getenv('BASE_RETRY_DELAY', 1))
        self.max_delay = int(os.getenv('MAX_RETRY_DELAY', 60))
        self.payment_retry = os.getenv('PAYMENT_RETRY', 'false').lower() == 'true'
        self.error_log = []
        self.queued_operations = []

    def handle_error(self, error: Exception, context: Dict[str, Any]) -> bool:
        """
        Handle error with appropriate recovery strategy

        Returns:
            bool: True if operation should be retried, False if not
        """

        # Categorize error
        category = self._categorize_error(error, context)

        # Special rule: NEVER retry payment actions
        if context.get('operation_type') == 'payment':
            self._create_error_alert(error, context, category, manual_required=True)
            self._log_error(error, context, category, attempts=1, final=True)
            return False

        # Log initial error
        self._log_error(error, context, category, attempts=1)

        # Handle based on category
        if category == ErrorCategory.TRANSIENT:
            return self._retry_with_backoff(error, context)

        elif category == ErrorCategory.AUTH:
            self._create_error_alert(error, context, category, manual_required=True)
            self._pause_operations(context.get('service'))
            return False

        elif category == ErrorCategory.LOGIC:
            self._queue_for_review(error, context)
            return False

        elif category == ErrorCategory.DATA:
            self._quarantine_data(context)
            self._create_error_alert(error, context, category)
            return False

        elif category == ErrorCategory.SYSTEM:
            self._trigger_watchdog(error, context)
            return False

        return False

    def _retry_with_backoff(self, error: Exception, context: Dict[str, Any]) -> bool:
        """Implement exponential backoff retry logic"""

        for attempt in range(1, self.max_attempts + 1):
            delay = min(self.base_delay * (2 ** (attempt - 1)), self.max_delay)

            try:
                # Wait before retry
                time.sleep(delay)

                # Attempt operation
                operation = context.get('operation')
                if operation:
                    result = operation()

                    # Log successful retry
                    self._log_success(context, attempt)
                    return True

            except Exception as retry_error:
                self._log_error(retry_error, context, ErrorCategory.TRANSIENT, attempt)

                if attempt == self.max_attempts:
                    # Max attempts reached - create alert
                    self._create_error_alert(retry_error, context, ErrorCategory.TRANSIENT)
                    return False

        return False

    def _categorize_error(self, error: Exception, context: Dict[str, Any]) -> ErrorCategory:
        """Categorize error based on type and context"""

        error_str = str(error).lower()
        error_type = type(error).__name__.lower()

        # Transient errors
        if any(keyword in error_str for keyword in ['timeout', 'connection', 'rate limit', 'temporary']):
            return ErrorCategory.TRANSIENT

        # Auth errors
        if any(keyword in error_str for keyword in ['unauthorized', 'expired', 'forbidden', 'token']):
            return ErrorCategory.AUTH

        # Data errors
        if any(keyword in error_str for keyword in ['file not found', 'permission denied', 'corrupted']):
            return ErrorCategory.DATA

        # System errors
        if any(keyword in error_str for keyword in ['disk full', 'memory', 'crash', 'unavailable']):
            return ErrorCategory.SYSTEM

        # Default to logic error
        return ErrorCategory.LOGIC
```

### Special Service Handlers

#### Gmail API Handler
```python
def handle_gmail_api_error(error: Exception, context: Dict[str, Any]):
    """Handle Gmail API specific errors"""

    if 'timeout' in str(error).lower() or 'service unavailable' in str(error).lower():
        # Queue emails locally
        queue_email = {
            'to': context.get('to'),
            'subject': context.get('subject'),
            'body': context.get('body'),
            'queued_at': datetime.now().isoformat(),
            'retry_after': 'service_restored'
        }

        # Add to local queue
        add_to_email_queue(queue_email)

        # Log and continue
        log_info('Gmail API down - email queued locally', queue_email)

        # Create gentle alert (not urgent)
        create_service_alert('gmail_api', 'Service temporarily unavailable - emails queued')
```

#### Banking API Handler
```python
def handle_banking_api_error(error: Exception, context: Dict[str, Any]):
    """Handle Banking API specific errors - NEVER retry"""

    # NEVER retry payment actions
    payment_context = {
        **context,
        'error': str(error),
        'timestamp': datetime.now().isoformat(),
        'requires_fresh_approval': True
    }

    # Create immediate alert
    alert_file = create_payment_error_alert(payment_context)

    # Log as critical
    log_critical('Banking API error - manual approval required', payment_context)

    # Stop all payment operations
    pause_payment_operations()

    # Notify human immediately
    send_urgent_notification('Banking API failure - manual intervention required')
```

#### Claude Code Handler
```python
def handle_claude_unavailable(error: Exception, context: Dict[str, Any]):
    """Handle Claude Code unavailability"""

    # Watchers keep collecting, queue grows
    queue_operation = {
        'operation': context.get('operation'),
        'data': context.get('data'),
        'queued_at': datetime.now().isoformat(),
        'queue_reason': 'claude_unavailable'
    }

    add_to_operation_queue(queue_operation)

    # Continue monitoring
    maintain_watchers()

    # Log for visibility
    log_warning('Claude unavailable - operation queued', queue_operation)
```

### Alert System

#### Error Alert Format
**Location:** `/Needs_Action/ERROR_<service>_<YYYY-MM-DD>.md`

```markdown
---
type: error_alert
error_category: transient
service: gmail_api
attempts_made: 3
last_error: "Connection timeout after 30 seconds"
action_required: manual_review
timestamp: 2026-01-07T10:30:00Z
operation_type: email_send
priority: medium
---

# Error Alert - Gmail API - 2026-01-07

## Error Details
- **Service:** Gmail API
- **Error Category:** Transient
- **Last Error:** Connection timeout after 30 seconds
- **Attempts Made:** 3/3
- **Timestamp:** 2026-01-07 10:30:00
- **Priority:** Medium

## Operation Context
- **Operation Type:** Email send
- **Target:** customer@example.com
- **Subject:** Invoice INV-2024-001
- **Data Size:** 2.3MB

## Retry History
1. **Attempt 1:** 10:28:30 - Failed (timeout)
2. **Attempt 2:** 10:29:32 - Failed (timeout) - waited 1s
3. **Attempt 3:** 10:30:36 - Failed (timeout) - waited 2s

## Analysis
- **Issue:** Persistent connection timeouts
- **Impact:** 3 emails queued locally
- **Root Cause:** Likely network or API issue
- **Auto-Recovery:** Exhausted all retries

## Recommended Actions
- [ ] Check Gmail API status page
- [ ] Verify network connectivity
- [ ] Check API quota limits
- [ ] Consider alternative email service
- [ ] Process queued emails when restored

## Manual Override Options
- **Retry Now:** `/error-recovery-retry --service gmail --operation email_123`
- **Skip to Queue:** `/error-recovery-skip --operation email_123`
- **Pause Service:** `/error-recovery-pause --service gmail`

---
*Auto-generated by Error Recovery System*
*Queue Status: 3 operations pending*
```

### Logging System

#### Error Log Format
**Location:** `/Logs/errors_YYYY-MM-DD.json`

```json
{
  "timestamp": "2026-01-07T10:30:00Z",
  "error_id": "err_abc123",
  "category": "transient",
  "service": "gmail_api",
  "operation": "email_send",
  "error_message": "Connection timeout after 30 seconds",
  "error_type": "TimeoutError",
  "context": {
    "to": "customer@example.com",
    "subject": "Invoice INV-2024-001",
    "retry_count": 3
  },
  "recovery_attempted": true,
  "recovery_successful": false,
  "final_action": "alert_created",
  "operator": "claude"
}
```

## Commands Reference

### Error Handling Commands
```bash
# Manually retry failed operation
/error-recovery-retry --operation email_123

# Skip operation and move to manual queue
/error-recovery-skip --operation email_123

# Pause service operations
/error-recovery-pause --service gmail

# Resume service operations
/error-recovery-resume --service gmail

# Check error status
/error-recovery-status --service gmail

# Clear error queue
/error-recovery-clear-queue --service gmail
```

### Queue Management Commands
```bash
# View queued operations
/error-recovery-queue --service gmail

# Process queued items
/error-recovery-process-queue --service gmail

# Queue status summary
/error-recovery-queue-status

# Force queue processing
/error-recovery-force-process
```

### Analysis Commands
```bash
# Error analysis for period
/error-recovery-analyze --period 24h

# Error breakdown by category
/error-recovery-breakdown --day 2026-01-07

# Service reliability report
/error-recovery-reliability --service gmail --period 7d

# Generate error report
/error-recovery-report --format markdown --period 30d
```

## Configuration

### Retry Configuration
```python
# Custom retry strategies
RETRY_CONFIGS = {
    'gmail_api': {
        'max_attempts': 3,
        'base_delay': 2,
        'max_delay': 30,
        'backoff_multiplier': 2
    },
    'banking_api': {
        'max_attempts': 0,  # NEVER retry
        'base_delay': 0,
        'max_delay': 0
    },
    'claude_api': {
        'max_attempts': 5,
        'base_delay': 1,
        'max_delay': 60,
        'backoff_multiplier': 2
    }
}
```

### Service-Specific Rules
```yaml
service_rules:
  gmail_api:
    queue_on_failure: true
    alert_threshold: 3
    pause_on_errors: 5

  banking_api:
    queue_on_failure: false
    retry_on_failure: false
    immediate_alert: true
    require_approval: true

  claude_api:
    queue_on_failure: true
    continue_monitoring: true
    alert_threshold: 10

  obsidian_vault:
    fallback_path: /tmp/
    sync_when_available: true
    alert_on_lock: true
```

## Integration Examples

### With Other Skills
```python
# Wrapper for API calls
def with_error_recovery(operation, context):
    """Wrap any operation with error recovery"""

    try:
        recovery_handler = ErrorRecoveryHandler()
        result = operation()

        # Clear any previous errors for this context
        clear_error_context(context)

        return result

    except Exception as e:
        recovery_handler.handle_error(e, context)

        # Return error state
        return {
            'success': False,
            'error': str(e),
            'recovery_attempted': True,
            'context': context
        }
```

### Payment Operation Example
```python
def process_payment(payment_data):
    """Process payment with strict error handling"""

    context = {
        'operation_type': 'payment',
        'amount': payment_data['amount'],
        'recipient': payment_data['recipient']
    }

    try:
        # Attempt payment
        result = banking_api.process_payment(payment_data)

        # Log success
        log_payment_success(payment_data)

        return result

    except Exception as e:
        # Handle with error recovery (will NOT retry)
        ErrorRecoveryHandler().handle_error(e, context)

        # Payment failed - manual approval required
        raise PaymentProcessingError("Payment failed - manual approval required")
```

## Performance Optimization

### Efficient Queue Management
```python
class OperationQueue:
    def __init__(self):
        self.queues = {
            'gmail': [],
            'claude': [],
            'general': []
        }
        self.max_queue_size = 1000

    def add_operation(self, service, operation):
        """Add operation to service-specific queue"""

        if len(self.queues[service]) >= self.max_queue_size:
            # Emergency: process oldest or alert
            self.handle_queue_overflow(service)

        self.queues[service].append({
            **operation,
            'queued_at': datetime.now(),
            'id': generate_operation_id()
        })

    def process_queue(self, service):
        """Process queued operations for service"""

        if self.is_service_available(service):
            operations = self.queues[service].copy()
            self.queues[service] = []

            for operation in operations:
                try:
                    execute_operation(operation)
                except Exception as e:
                    # Re-queue if still transient
                    if is_transient_error(e):
                        self.queues[service].append(operation)
```

## Best Practices

1. **Never Retry Payments**: Always require fresh approval
2. **Log Everything**: Comprehensive logging for debugging
3. **Alert Appropriately**: Right level of urgency
4. **Queue Gracefully**: Don't lose operations during outages
5. **Monitor Health**: Track error rates and patterns
6. **Test Failures**: Regular failure scenario testing

## Troubleshooting

### Common Issues
1. **"Excessive retries"**
   - Check max retry configuration
   - Review error categorization
   - Adjust backoff delays

2. **"Queue growing too large"**
   - Check service availability
   - Process queue manually
   - Review failure patterns

3. **"Missing error alerts"**
   - Verify alert generation logic
   - Check file permissions
   - Review alert thresholds

4. **"Payments stuck"**
   - Always expected behavior
   - Check for approval files
   - Manual approval required

## Security Considerations

1. **Error Information**: Don't log sensitive data
2. **Queue Security**: Encrypt sensitive queued operations
3. **Access Control**: Limit error log access
4. **Data Retention**: Define log retention policies
5. **Audit Trail**: Maintain complete error history