---
name: circuit-breaker
description: Prevent cascade failures when services go down with circuit breaker pattern implementation. Monitors service health, trips on consecutive failures, and automatically recovers with half-open testing. Use when Claude needs to: (1) Prevent system-wide collapse from service failures, (2) Monitor service health in real-time, (3) Automatically block failing services, (4) Test service recovery safely, (5) Update dashboard with service status
license: Complete terms in LICENSE.txt
---

# Circuit Breaker

This skill implements the circuit breaker pattern to prevent cascade failures when services go down, automatically blocking failing services and testing for recovery.

## Prerequisites

### Environment Configuration
Required `.env` variables:
```bash
FAILURE_THRESHOLD=5
COOLDOWN_SECONDS=60
HALF_OPEN_TRIAL=1
CIRCUIT_BREAKER_LOG=/Logs/circuit_breaker_status.json
```

## Circuit Breaker States

### CLOSED (Normal Operation)
- All requests flow through normally
- Failure counter resets on success
- Service considered healthy

### OPEN (Service Failing)
- All requests blocked immediately
- No calls reach the failing service
- Cooldown period active
- Prevents cascade failures

### HALF-OPEN (Testing Recovery)
- Allows 1 trial request after cooldown
- Tests if service has recovered
- Resets to CLOSED on success
- Returns to OPEN on failure

## Core Implementation

### Circuit Breaker Class

```python
import time
import json
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional, Callable
from threading import Lock

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.failure_threshold = int(os.getenv('FAILURE_THRESHOLD', 5))
        self.cooldown_seconds = int(os.getenv('COOLDOWN_SECONDS', 60))
        self.half_open_trial = int(os.getenv('HALF_OPEN_TRIAL', 1))

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.tripped_time = None
        self.half_open_attempts = 0

        self.lock = Lock()
        self.status_file = os.getenv('CIRCUIT_BREAKER_LOG', '/Logs/circuit_breaker_status.json')

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""

        with self.lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_attempts = 0
                    self._log_state_change("OPEN → HALF_OPEN")
                else:
                    raise CircuitBreakerOpenError(f"Circuit breaker OPEN for {self.service_name}")

            try:
                # Attempt the operation
                result = func(*args, **kwargs)

                # Success!
                self._on_success()
                return result

            except Exception as e:
                # Failure
                self._on_failure()
                raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.tripped_time is None:
            return False

        time_since_trip = datetime.now() - self.tripped_time
        return time_since_trip.total_seconds() >= self.cooldown_seconds

    def _on_success(self):
        """Handle successful operation"""
        if self.state == CircuitState.HALF_OPEN:
            # Service recovered!
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.tripped_time = None
            self._log_state_change("HALF_OPEN → CLOSED (RECOVERED)")
            self._update_dashboard("recovered")
        else:
            # Normal operation in CLOSED state
            self.failure_count = 0

    def _on_failure(self):
        """Handle failed operation"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.state == CircuitState.HALF_OPEN:
            # Failed during half-open test - trip again
            self.state = CircuitState.OPEN
            self.tripped_time = datetime.now()
            self._log_state_change("HALF_OPEN → OPEN (RECOVERY FAILED)")
            self._update_dashboard("tripped")

        elif self.failure_count >= self.failure_threshold:
            # Too many failures - trip the breaker
            self.state = CircuitState.OPEN
            self.tripped_time = datetime.now()
            self._log_state_change("CLOSED → OPEN (TRIPPED)")
            self._update_dashboard("tripped")

    def _log_state_change(self, change: str):
        """Log state change to file"""
        log_entry = {
            "service": self.service_name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "tripped_at": self.tripped_time.isoformat() if self.tripped_time else None,
            "retry_after": (self.tripped_time + timedelta(seconds=self.cooldown_seconds)).isoformat() if self.tripped_time else None,
            "state_change": change,
            "timestamp": datetime.now().isoformat()
        }

        # Write to status file
        self._write_status_file(log_entry)

        # Log to main log
        log_info(f"Circuit Breaker: {self.service_name} - {change}")

    def _write_status_file(self, entry: Dict[str, Any]):
        """Write current status to file"""
        try:
            # Read existing status
            status_data = {}
            if os.path.exists(self.status_file):
                with open(self.status_file, 'r') as f:
                    status_data = json.load(f)

            # Update service status
            status_data[self.service_name] = entry

            # Write back
            with open(self.status_file, 'w') as f:
                json.dump(status_data, f, indent=2)

        except Exception as e:
            log_error(f"Failed to write circuit breaker status: {str(e)}")

    def _update_dashboard(self, event: str):
        """Update Dashboard.md with breaker status"""
        try:
            dashboard_file = "Dashboard.md"

            if event == "tripped":
                alert = f"⚠️ CIRCUIT BREAKER: {self.service_name} is DOWN (tripped at {self.tripped_time.strftime('%H:%M')})"
                add_dashboard_alert(dashboard_file, alert, priority="high")

            elif event == "recovered":
                alert = f"✅ CIRCUIT BREAKER: {self.service_name} is RECOVERED (restored at {datetime.now().strftime('%H:%M')})"
                add_dashboard_alert(dashboard_file, alert, priority="info")

        except Exception as e:
            log_error(f"Failed to update dashboard: {str(e)}")
```

### Service Manager

```python
class CircuitBreakerManager:
    def __init__(self):
        self.breakers = {}
        self.monitored_services = [
            'gmail_api',
            'facebook_graph_api',
            'instagram_graph_api',
            'x_twitter_api',
            'odoo_json_rpc',
            'whatsapp_web'
        ]

        # Initialize breakers for all services
        for service in self.monitored_services:
            self.breakers[service] = CircuitBreaker(service)

    def get_breaker(self, service_name: str) -> CircuitBreaker:
        """Get circuit breaker for service"""
        if service_name not in self.breakers:
            self.breakers[service_name] = CircuitBreaker(service)
        return self.breakers[service_name]

    def call_service(self, service_name: str, func: Callable, *args, **kwargs) -> Any:
        """Execute service call with circuit breaker protection"""
        breaker = self.get_breaker(service_name)
        return breaker.call(func, *args, **kwargs)

    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers"""
        status = {}
        for service, breaker in self.breakers.items():
            status[service] = {
                'state': breaker.state.value,
                'failure_count': breaker.failure_count,
                'tripped_at': breaker.tripped_time.isoformat() if breaker.tripped_time else None,
                'retry_after': (breaker.tripped_time + timedelta(seconds=breaker.cooldown_seconds)).isoformat() if breaker.tripped_time else None
            }
        return status

# Global instance
circuit_breaker_manager = CircuitBreakerManager()
```

## Integration with Services

### Gmail API Integration
```python
def send_gmail_with_breaker(to: str, subject: str, body: str):
    """Send Gmail with circuit breaker protection"""

    def _send_email():
        return gmail_service.send_message(to, subject, body)

    try:
        return circuit_breaker_manager.call_service('gmail_api', _send_email)
    except CircuitBreakerOpenError:
        # Circuit is open - queue email locally
        queue_email_locally(to, subject, body)
        log_warning("Gmail circuit breaker open - email queued")
        return None
```

### Odoo Integration
```python
def create_odoo_invoice_with_breaker(invoice_data: Dict[str, Any]):
    """Create Odoo invoice with circuit breaker protection"""

    def _create_invoice():
        return odoo_client.create_invoice(invoice_data)

    try:
        return circuit_breaker_manager.call_service('odoo_json_rpc', _create_invoice)
    except CircuitBreakerOpenError:
        # Circuit is open - queue for later
        queue_invoice_for_retry(invoice_data)
        log_warning("Odoo circuit breaker open - invoice queued")
        return None
```

### X/Twitter Integration
```python
def post_tweet_with_breaker(text: str):
    """Post tweet with circuit breaker protection"""

    def _post_tweet():
        return twitter_client.create_tweet(text)

    try:
        return circuit_breaker_manager.call_service('x_twitter_api', _post_tweet)
    except CircuitBreakerOpenError:
        # Circuit is open - queue tweet
        queue_tweet_for_later(text)
        log_warning("Twitter circuit breaker open - tweet queued")
        return None
```

## Status File Format

### Circuit Breaker Status (`/Logs/circuit_breaker_status.json`)
```json
{
  "gmail_api": {
    "service": "gmail_api",
    "state": "OPEN",
    "failure_count": 5,
    "tripped_at": "2026-01-07T10:30:00Z",
    "retry_after": "2026-01-07T10:31:00Z",
    "state_change": "CLOSED → OPEN (TRIPPED)",
    "timestamp": "2026-01-07T10:30:00Z"
  },
  "facebook_graph_api": {
    "service": "facebook_graph_api",
    "state": "CLOSED",
    "failure_count": 0,
    "tripped_at": null,
    "retry_after": null,
    "state_change": "HALF_OPEN → CLOSED (RECOVERED)",
    "timestamp": "2026-01-07T10:29:30Z"
  },
  "instagram_graph_api": {
    "service": "instagram_graph_api",
    "state": "CLOSED",
    "failure_count": 0,
    "tripped_at": null,
    "retry_after": null,
    "state_change": "Normal operation",
    "timestamp": "2026-01-07T09:00:00Z"
  },
  "x_twitter_api": {
    "service": "x_twitter_api",
    "state": "HALF_OPEN",
    "failure_count": 5,
    "tripped_at": "2026-01-07T10:15:00Z",
    "retry_after": "2026-01-07T10:16:00Z",
    "state_change": "OPEN → HALF_OPEN",
    "timestamp": "2026-01-07T10:16:00Z"
  },
  "odoo_json_rpc": {
    "service": "odoo_json_rpc",
    "state": "CLOSED",
    "failure_count": 0,
    "tripped_at": null,
    "retry_after": null,
    "state_change": "Normal operation",
    "timestamp": "2026-01-07T09:00:00Z"
  },
  "whatsapp_web": {
    "service": "whatsapp_web",
    "state": "CLOSED",
    "failure_count": 0,
    "tripped_at": null,
    "retry_after": null,
    "state_change": "Normal operation",
    "timestamp": "2026-01-07T09:00:00Z"
  }
}
```

## Dashboard Integration

### Dashboard.md Updates
```markdown
## System Status

### Circuit Breakers
| Service | Status | Failures | Last Event |
|---------|--------|----------|------------|
| Gmail API | ⚠️ OPEN | 5 | Tripped at 10:30 |
| Facebook API | ✅ CLOSED | 0 | Recovered at 10:29 |
| Instagram API | ✅ CLOSED | 0 | Normal |
| X/Twitter API | 🟡 HALF-OPEN | 5 | Testing at 10:16 |
| Odoo JSON-RPC | ✅ CLOSED | 0 | Normal |
| WhatsApp Web | ✅ CLOSED | 0 | Normal |

### Recent Alerts
- ⚠️ CIRCUIT BREAKER: gmail_api is DOWN (tripped at 10:30)
- ✅ CIRCUIT BREAKER: facebook_graph_api is RECOVERED (restored at 10:29)
```

## Commands Reference

### Status Commands
```bash
# Check all circuit breaker status
/circuit-breaker-status

# Check specific service
/circuit-breaker-status --service gmail_api

# Get detailed report
/circuit-breaker-report --format json

# Check tripped services
/circuit-breaker-tripped

# Check services in half-open
/circuit-breaker-half-open
```

### Manual Control Commands
```bash
# Manually trip a breaker (for testing)
/circuit-breaker-trip --service gmail_api --reason "Manual test"

# Manually reset a breaker
/circuit-breaker-reset --service gmail_api

# Force half-open state
/circuit-breaker-half-open --service gmail_api

# Configure thresholds
/circuit-breaker-config --service gmail_api --threshold 3 --cooldown 30
```

### Testing Commands
```bash
# Test circuit breaker behavior
/circuit-breaker-test --service gmail_api --failures 6

# Simulate service recovery
/circuit-breaker-test-recovery --service gmail_api

# Health check all services
/circuit-breaker-health-check
```

## Error Handling

### Circuit Breaker Open Exception
```python
class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open"""

    def __init__(self, service_name: str):
        self.service_name = service_name
        super().__init__(f"Circuit breaker OPEN for {service_name}")
```

### Fallback Strategies
```python
def with_fallback(service_name: str, primary_func: Callable, fallback_func: Callable):
    """Execute with fallback when circuit is open"""

    try:
        return circuit_breaker_manager.call_service(service_name, primary_func)
    except CircuitBreakerOpenError:
        log_warning(f"Circuit open for {service_name}, using fallback")
        return fallback_func()
```

## Performance Monitoring

### Metrics Collection
```python
def collect_circuit_breaker_metrics():
    """Collect metrics for monitoring"""

    metrics = {
        'timestamp': datetime.now().isoformat(),
        'services': {}
    }

    for service, breaker in circuit_breaker_manager.breakers.items():
        metrics['services'][service] = {
            'state': breaker.state.value,
            'failure_count': breaker.failure_count,
            'time_in_state': calculate_time_in_state(breaker),
            'total_trips': get_total_trips(service)
        }

    # Send to monitoring system
    send_metrics(metrics)
```

## Best Practices

1. **Configure Appropriate Thresholds**: Set based on service reliability
2. **Monitor Circuit State**: Regular checks on breaker status
3. **Implement Fallbacks**: Always have backup plans
4. **Log State Changes**: Track all breaker transitions
5. **Test Recovery**: Verify half-open behavior
6. **Dashboard Visibility**: Keep status visible

## Troubleshooting

### Common Issues
1. **"Circuit breaker always open"**
   - Check failure threshold
   - Verify service is actually failing
   - Review cooldown period

2. **"Service not being blocked"**
   - Verify circuit breaker is being used
   - Check service name matches
   - Review failure counting logic

3. **"Recovery not working"**
   - Check half-open trial count
   - Verify cooldown period
   - Review success detection logic

4. **"Status file not updating"**
   - Check file permissions
   - Verify path exists
   - Review write logic

## Integration Examples

### Decorator Pattern
```python
def with_circuit_breaker(service_name: str):
    """Decorator for circuit breaker protection"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            return circuit_breaker_manager.call_service(service_name, func, *args, **kwargs)
        return wrapper
    return decorator

# Usage
@with_circuit_breaker('gmail_api')
def send_email(to, subject, body):
    return gmail_service.send_message(to, subject, body)
```

### Context Manager Pattern
```python
from contextlib import contextmanager

@contextmanager
def circuit_breaker_context(service_name: str):
    """Context manager for circuit breaker"""

    breaker = circuit_breaker_manager.get_breaker(service_name)

    if breaker.state == CircuitState.OPEN:
        raise CircuitBreakerOpenError(service_name)

    try:
        yield breaker
    except Exception as e:
        breaker._on_failure()
        raise
    else:
        breaker._on_success()

# Usage
with circuit_breaker_context('gmail_api') as breaker:
    result = gmail_service.send_message(to, subject, body)
```

## Security Considerations

1. **Status File Access**: Restrict access to status files
2. **Configuration Security**: Secure threshold settings
3. **Audit Trail**: Log all manual interventions
4. **Monitoring Access**: Control who can view status
5. **Reset Permissions**: Limit who can reset breakers