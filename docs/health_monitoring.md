# Health Monitoring System

The AI Employee system includes a comprehensive health monitoring system that tracks system resources, service availability, and performance metrics in real-time.

## Overview

The health monitoring system provides:
- **System Resource Monitoring**: CPU, memory, disk usage tracking
- **Service Availability Checks**: Monitor internal and external services
- **Performance Metrics**: Response times, queue depths, error rates
- **Anomaly Detection**: Automatic detection of unusual patterns
- **Alert Management**: Configurable alerts with multiple severity levels
- **Health Reports**: Detailed periodic health reports
- **API Endpoints**: RESTful API for accessing health data

## Architecture

### Core Components

1. **HealthMonitor**: Main orchestrator for all health checks
2. **HealthCheck**: Individual check configuration and results
3. **HealthMetric**: Metric data with threshold evaluation
4. **HealthReport**: Comprehensive health snapshot
5. **HealthAlert**: Alert events with acknowledgment workflow

### Integration Points

- **Event Bus**: Publishes health status change events
- **Error Recovery**: Monitors error rates and system recovery
- **Configuration**: Thresholds and check intervals configurable
- **Logging**: Structured logging for all health events

## Usage

### Basic Setup

```python
from ai_employee.utils.health_monitor import get_health_monitor, initialize_health_monitor

# Initialize and start monitoring
await initialize_health_monitor()

# Get the monitor instance
monitor = get_health_monitor()

# Run a health check
result = await monitor.run_check("cpu_usage")
print(f"CPU Usage: {result.metrics[0].value}%")
```

### Registering Custom Health Checks

```python
from ai_employee.utils.health_monitor import health_check, CheckType

@health_check(
    name="database_connection",
    check_type=CheckType.DATABASE,
    interval=30,
    timeout=10
)
async def check_database_health(check):
    """Check database connectivity and performance."""
    # Your check logic here
    return [
        {
            "name": "connection_time",
            "value": 15.2,
            "unit": "ms",
            "threshold_warning": 100.0,
            "threshold_critical": 500.0
        }
    ]
```

### Monitoring System Resources

The system automatically monitors:

- **CPU Usage**: Total CPU percentage and load average
- **Memory**: Virtual memory and swap usage
- **Disk Space**: Usage for all mounted filesystems
- **File System**: Accessibility of critical paths

### Service Health Checks

Monitor external services:

```python
monitor.register_check(
    name="api_service",
    check_type=CheckType.SERVICE_AVAILABILITY,
    description="External API health",
    interval=60,
    service_config={
        "host": "api.example.com",
        "port": 443,
        "type": "http",
        "health_url": "https://api.example.com/health"
    }
)
```

## API Endpoints

### Health Status

- `GET /health/` - Overall system health status
- `GET /health/detailed` - Full health report with all metrics
- `GET /health/summary` - Concise summary for dashboards

### Health Checks

- `GET /health/checks` - List all health checks
- `GET /health/checks/{name}` - Get specific check details
- `POST /health/checks/{name}/run` - Run check immediately
- `PUT /health/checks/{name}/enable` - Enable a check
- `PUT /health/checks/{name}/disable` - Disable a check

### Metrics

- `GET /health/metrics` - Get system and service metrics
- `GET /health/metrics?metric_name=cpu_usage` - Specific metric with history

### Alerts

- `GET /health/alerts` - List health alerts
- `POST /health/alerts/{id}/acknowledge` - Acknowledge an alert
- `POST /health/alerts/{id}/resolve` - Resolve an alert

### Probes

- `GET /health/ping` - Simple ping for load balancers
- `GET /health/live` - Kubernetes liveness probe
- `GET /health/ready` - Kubernetes readiness probe

## Configuration

### Default Thresholds

System-wide default thresholds:

```python
CPU_WARNING_THRESHOLD = 70.0%  # CPU usage warning
CPU_CRITICAL_THRESHOLD = 90.0%  # CPU usage critical

MEMORY_WARNING_THRESHOLD = 75.0%  # Memory usage warning
MEMORY_CRITICAL_THRESHOLD = 90.0%  # Memory usage critical

DISK_WARNING_THRESHOLD = 80.0%  # Disk usage warning
DISK_CRITICAL_THRESHOLD = 95.0%  # Disk usage critical
```

### Custom Configuration

Configure thresholds in your environment:

```python
# config.py
MONITORING_CONFIG = {
    "cpu_usage": {
        "threshold_warning": 60.0,
        "threshold_critical": 85.0,
        "interval": 30
    },
    "memory_usage": {
        "threshold_warning": 80.0,
        "threshold_critical": 95.0,
        "interval": 30
    }
}
```

## Alert Management

### Alert Levels

- **INFO**: Informational alerts
- **WARNING**: Warning level issues
- **ERROR**: Error conditions
- **CRITICAL**: Critical system failures

### Alert Workflow

1. **Detection**: Metric exceeds threshold
2. **Alert Creation**: Alert generated with severity
3. **Notification**: Event published to event bus
4. **Acknowledgment**: Manual acknowledgment by operator
5. **Resolution**: Automatic or manual resolution

### Alert Operations

```python
# Get active alerts
alerts = await monitor.get_active_alerts()

# Acknowledge an alert
await monitor.acknowledge_alert(alert_id, "operator_name")

# Resolve an alert
await monitor.resolve_alert(alert_id)
```

## Integration with Error Recovery

The health monitor integrates with the error recovery system:

```python
# Error recovery registers its own health checks
- error_rate_per_minute: Monitors error frequency
- circuit_breaker_status: Tracks circuit breaker state
- error_recovery_queues: Monitors queue depths
```

## Performance Considerations

### Optimization Tips

1. **Check Intervals**: Set appropriate intervals for each check type
2. **Timeouts**: Configure reasonable timeouts for external checks
3. **Batch Operations**: Group related checks to minimize overhead
4. **Historical Data**: Limit history retention to manage memory

### Resource Usage

- CPU: Minimal overhead from lightweight checks
- Memory: Configurable history retention (default 1000 points)
- Network: Only for external service checks
- Storage: Periodic health reports saved to disk

## Troubleshooting

### Common Issues

1. **Checks Not Running**
   - Verify health monitor is initialized
   - Check if checks are enabled
   - Review error logs

2. **False Positives**
   - Adjust threshold values
   - Increase check intervals
   - Check metric calculations

3. **Missing Metrics**
   - Verify check implementations
   - Check for permission issues
   - Review data collection methods

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger("ai_employee.utils.health_monitor").setLevel(logging.DEBUG)
```

## Best Practices

1. **Start Simple**: Begin with basic system resource checks
2. **Custom Thresholds**: Set thresholds based on your environment
3. **Monitor Dependencies**: Check all critical dependencies
4. **Regular Reviews**: Periodically review and update checks
5. **Alert Fatigue**: Configure appropriate alert levels to avoid noise

## Example Dashboard Integration

```javascript
// Frontend integration example
async function fetchHealthSummary() {
    const response = await fetch('/api/health/summary');
    const health = await response.json();

    updateDashboard({
        status: health.overall_status,
        uptime: health.uptime_percentage,
        alerts: health.alerts.active,
        checks: health.checks
    });
}
```

## Security Considerations

- Health endpoints are read-only
- No sensitive data exposed in metrics
- Rate limiting recommended for public endpoints
- Authentication can be added for protected endpoints

## Extending the System

### Custom Check Types

Implement new check types by extending the HealthCheck class:

```python
class CustomHealthCheck(HealthCheck):
    async def execute(self):
        # Custom implementation
        pass
```

### Custom Metrics

Create specialized metrics:

```python
from ai_employee.utils.health_monitor import HealthMetric

metric = HealthMetric(
    name="custom_metric",
    value=calculate_value(),
    unit="custom_unit",
    threshold_warning=100.0,
    threshold_critical=200.0
)
```

### Integration Hooks

- Event bus subscribers for health events
- Custom alert handlers
- External monitoring system integration
- Webhook notifications for critical alerts