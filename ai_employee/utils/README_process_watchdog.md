# Process Watchdog System

The Process Watchdog is a comprehensive system for monitoring and automatically restarting failed processes in the AI Employee system. It provides intelligent restart strategies, health monitoring, and comprehensive failure tracking.

## Features

### Core Capabilities
- **Process Health Monitoring**: Continuous monitoring of process status, CPU usage, memory consumption, and custom health endpoints
- **Automatic Restart**: Intelligent restart mechanisms with configurable backoff strategies
- **Failure Tracking**: Comprehensive history of restarts, crashes, and recovery attempts
- **Health Checks**: Built-in health check types and support for custom health endpoints
- **Event Integration**: Publishes process lifecycle events to the event bus
- **Statistics & Reporting**: Detailed metrics on uptime, restart counts, and failure patterns

### Restart Strategies
1. **Immediate**: Restart immediately without delay
2. **Exponential Backoff**: Increasing delays between restart attempts (default)
3. **Linear Backoff**: Linear increase in delay between attempts
4. **Fixed Interval**: Constant delay between restart attempts
5. **No Restart**: Disable automatic restarting

### Health Check Types
- **Heartbeat**: Basic process liveness check
- **CPU Usage**: Monitor CPU consumption with thresholds
- **Memory Usage**: Monitor memory usage with limits
- **Response Time**: Check process responsiveness
- **Custom Endpoint**: HTTP endpoint health checks

## Quick Start

### Basic Usage

```python
from ai_employee.utils import get_process_watchdog, initialize_process_watchdog

# Initialize the watchdog
await initialize_process_watchdog()

# Get the watchdog instance
watchdog = get_process_watchdog()

# Register a process
await watchdog.register_process(
    name="my_service",
    command=["python", "service.py"],
    auto_restart=True,
    restart_strategy=RestartStrategy.EXPONENTIAL_BACKOFF,
    max_restarts=5
)

# Start the process
await watchdog.start_process("my_service")
```

### Using the Decorator

```python
from ai_employee.utils.process_watchdog import monitor_process

@monitor_process(
    name="decorated_service",
    auto_restart=True,
    max_restarts=3
)
async def my_service():
    # Your service code here
    while True:
        await do_work()
        await asyncio.sleep(1)
```

## Configuration

### Process Registration Options

```python
await watchdog.register_process(
    name="service_name",           # Unique process name
    command=["python", "app.py"],  # Command to execute
    working_dir="/app/dir",        # Working directory (optional)
    env={"VAR": "value"},          # Environment variables
    auto_restart=True,             # Enable auto-restart
    restart_strategy=RestartStrategy.EXPONENTIAL_BACKOFF,
    max_restarts=5,                # Maximum restart attempts
    health_checks=[                # Health checks to perform
        HealthCheckType.HEARTBEAT,
        HealthCheckType.CPU_USAGE
    ],
    backoff_config=BackoffConfig(  # Custom backoff settings
        base_delay=1.0,
        max_delay=300.0,
        multiplier=2.0,
        jitter=True
    )
)
```

### Backoff Configuration

```python
from ai_employee.utils.process_watchdog import BackoffConfig, RestartStrategy

# Exponential backoff (default)
backoff = BackoffConfig(
    strategy=RestartStrategy.EXPONENTIAL_BACKOFF,
    base_delay=1.0,     # Initial delay
    max_delay=300.0,    # Maximum delay
    multiplier=2.0,     # Delay multiplier
    jitter=True         # Add random jitter
)

# Fixed interval
backoff = BackoffConfig(
    strategy=RestartStrategy.FIXED_INTERVAL,
    base_delay=10.0     # Constant delay
)
```

## Monitoring & Management

### Process Status

```python
# Get status of a single process
status = await watchdog.get_process_status("my_service")
print(f"Status: {status.status}")
print(f"Uptime: {status.uptime} seconds")
print(f"Restarts: {status.restart_count}")

# Get all processes
all_processes = await watchdog.get_all_processes()
for name, info in all_processes.items():
    print(f"{name}: {info.status.value}")
```

### Restart History

```python
# Get restart history for a process
history = await watchdog.get_restart_history("my_service", limit=10)
for record in history:
    print(f"{record.timestamp}: {record.reason} - Success: {record.successful}")

# Get uptime percentage
uptime = await watchdog.calculate_uptime("my_service", hours=24)
print(f"24h uptime: {uptime:.1f}%")
```

### Process Control

```python
# Stop a process
await watchdog.stop_process("my_service")

# Force kill
await watchdog.stop_process("my_service", force=True)

# Manual restart
await watchdog.restart_process("my_service", reason="manual_update")

# Unregister from monitoring
await watchdog.unregister_process("my_service")
```

## Health Checks

### Built-in Health Checks

```python
await watchdog.register_process(
    name="monitored_service",
    command=["python", "service.py"],
    health_checks=[
        HealthCheckType.HEARTBEAT,        # Basic liveness
        HealthCheckType.CPU_USAGE,        # CPU threshold
        HealthCheckType.MEMORY_USAGE,     # Memory limit
        HealthCheckType.RESPONSE_TIME     # Response time check
    ]
)
```

### Custom Health Check Endpoint

```python
# Process with HTTP health endpoint
await watchdog.register_process(
    name="web_service",
    command=["uvicorn", "app:app"],
    health_checks=[HealthCheckType.CUSTOM_ENDPOINT],
    endpoint="http://localhost:8000/health"
)
```

### Custom Health Check Function

```python
async def custom_health_check(process_info):
    """Custom health check implementation."""
    # Your health check logic
    if check_condition():
        return True
    return False

# Register with custom function
await watchdog.register_process(
    name="custom_service",
    command=["python", "app.py"],
    health_checks=[HealthCheckType.CUSTOM_ENDPOINT],
    custom_function=custom_health_check
)
```

## Event Integration

The Process Watchdog publishes events to the event bus:

### Event Types

- **`ProcessWatchdogEvent`**: Process lifecycle events
  - `event_type`: "started", "stopped", "crashed", "restarted", "health_failed"
  - `process_name`: Name of the process
  - `pid`: Process ID
  - `status`: Current process status
  - `metrics`: Process metrics (CPU, memory, uptime)

### Event Handling

```python
from ai_employee.core.event_bus import get_event_bus
from ai_employee.utils.process_watchdog import ProcessWatchdogEvent

event_bus = get_event_bus()

async def handle_process_event(event: ProcessWatchdogEvent):
    if event.event_type == "crashed":
        logger.error(f"Process {event.process_name} crashed!")
        # Trigger alert or notification

    if event.event_type == "health_failed":
        logger.warning(f"Health check failed for {event.process_name}")
        # Take corrective action

await event_bus.subscribe(ProcessWatchdogEvent, handle_process_event)
```

## Integration with Other Systems

### Health Monitor Integration

The Process Watchdog automatically registers health checks with the system health monitor:

- Process uptime tracking
- Restart rate monitoring
- Error rate tracking

### Error Recovery Integration

When processes crash, the watchdog can trigger error recovery workflows:

```python
from ai_employee.utils.error_recovery import ErrorRecoveryService

# Error recovery is automatically triggered for critical process failures
# No additional configuration needed
```

## Configuration File

You can persist process configurations:

```json
{
  "processes": [
    {
      "name": "web_server",
      "command": ["uvicorn", "main:app", "--port", "8000"],
      "auto_restart": true,
      "restart_strategy": "exponential_backoff",
      "max_restarts": 5,
      "health_checks": ["heartbeat", "cpu_usage"]
    }
  ],
  "stats": {
    "total_restarts": 0,
    "process_crashes": 0
  },
  "timestamp": "2024-01-01T00:00:00"
}
```

## Best Practices

### 1. Process Design
- Keep processes idempotent and stateless where possible
- Implement graceful shutdown handling
- Include health endpoints for HTTP services
- Log structured messages for debugging

### 2. Configuration
- Set appropriate `max_restarts` based on service criticality
- Use exponential backoff for production services
- Configure health checks appropriate to service type
- Set meaningful thresholds for CPU/memory checks

### 3. Monitoring
- Set up alerts for critical process failures
- Track restart patterns for early failure detection
- Monitor aggregate uptime metrics
- Review restart history regularly

### 4. Production Deployment
- Use different backoff strategies for different services
- Implement process dependencies correctly
- Configure resource limits appropriately
- Test crash recovery procedures

## Examples

See the example files for detailed implementations:
- `test_process_watchdog.py`: Basic testing scenarios
- `example_process_watchdog_config.py`: Complete configuration example

## Troubleshooting

### Common Issues

1. **Process not restarting**
   - Check `max_restarts` limit
   - Verify `auto_restart` is enabled
   - Check process configuration

2. **False health check failures**
   - Adjust thresholds for CPU/memory checks
   - Increase check intervals if needed
   - Implement custom health checks

3. **High restart frequency**
   - Check for memory leaks or deadlocks
   - Increase backoff delays
   - Review application logs

### Debug Logging

Enable debug logging to troubleshoot issues:

```python
from ai_employee.utils.logging_config import configure_logging
configure_logging(level="DEBUG")
```

## API Reference

### Classes

- `ProcessWatchdog`: Main watchdog system
- `ProcessInfo`: Process information and status
- `RestartHistory`: History of restart attempts
- `HealthCheckConfig`: Configuration for health checks
- `BackoffConfig`: Configuration for backoff strategies

### Enums

- `ProcessStatus`: Running states and statuses
- `RestartStrategy`: Available restart strategies
- `HealthCheckType`: Types of health checks

### Functions

- `get_process_watchdog()`: Get global watchdog instance
- `initialize_process_watchdog()`: Initialize the system
- `monitor_process()`: Decorator for process monitoring

## License

This module is part of the AI Employee system. See the main project license for details.