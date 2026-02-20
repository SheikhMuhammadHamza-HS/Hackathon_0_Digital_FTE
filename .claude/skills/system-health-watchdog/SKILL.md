---
name: system-health-watchdog
description: Monitor system health and auto-heal critical processes with watchdog implementation. Monitors orchestrator, watchers, disk space, API credentials, and Obsidian vault. Auto-restarts crashed processes and generates hourly health reports. Use when Claude needs to: (1) Monitor critical system processes, (2) Auto-heal failed components, (3) Check system resources, (4) Verify service health, (5) Generate health reports
license: Complete terms in LICENSE.txt
---

# System Health Watchdog

This skill implements comprehensive system health monitoring and auto-healing capabilities following hackathon guide Section 7.4 specifications.

## Monitored Components

### Critical Processes (Auto-Restart Enabled)
- **orchestrator.py** - Main system orchestrator
- **gmail_watcher** - Gmail monitoring service
- **whatsapp_watcher** - WhatsApp monitoring service
- **filesystem_watch** - File system monitoring
- **social_listener** - Social media monitoring

### System Resources
- **Disk Space** - Alert if < 1GB free
- **Memory Usage** - Monitor for exhaustion
- **CPU Usage** - Track system load
- **Network Connectivity** - Verify connections

### Service Health
- **Odoo Connection** - Verify JSON-RPC access
- **API Credentials** - Check token expiration
- **Obsidian Vault** - Verify vault accessibility
- **Database Connections** - Verify data stores

## Health Check Intervals

| Check Type | Frequency | Purpose |
|------------|-----------|---------|
| Process Alive | Every 60 seconds | Detect crashes |
| Disk Space | Every 10 minutes | Prevent full disk |
| API Token Validity | Every 6 hours | Avoid auth failures |
| Full System Report | Every 1 hour | Comprehensive status |
| Obsidian Vault | Every 5 minutes | Ensure accessibility |

## Implementation Details

### Watchdog Manager

```python
import psutil
import os
import json
import subprocess
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

class HealthStatus(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"

@dataclass
class ProcessInfo:
    name: str
    pid: Optional[int]
    status: HealthStatus
    uptime: Optional[timedelta]
    restart_count: int
    last_restart: Optional[datetime]
    auto_restart: bool
    command: List[str]

class SystemHealthWatchdog:
    def __init__(self):
        self.monitored_processes = {
            'orchestrator.py': ProcessInfo(
                name='orchestrator.py',
                pid=None,
                status=HealthStatus.UNKNOWN,
                uptime=None,
                restart_count=0,
                last_restart=None,
                auto_restart=True,
                command=['python', 'orchestrator.py']
            ),
            'gmail_watcher': ProcessInfo(
                name='gmail_watcher',
                pid=None,
                status=HealthStatus.UNKNOWN,
                uptime=None,
                restart_count=0,
                last_restart=None,
                auto_restart=True,
                command=['python', 'gmail_watcher.py']
            ),
            'whatsapp_watcher': ProcessInfo(
                name='whatsapp_watcher',
                pid=None,
                status=HealthStatus.UNKNOWN,
                uptime=None,
                restart_count=0,
                last_restart=None,
                auto_restart=True,
                command=['python', 'whatsapp_watcher.py']
            ),
            'filesystem_watch': ProcessInfo(
                name='filesystem_watch',
                pid=None,
                status=HealthStatus.UNKNOWN,
                uptime=None,
                restart_count=0,
                last_restart=None,
                auto_restart=True,
                command=['python', 'filesystem_watch.py']
            ),
            'social_listener': ProcessInfo(
                name='social_listener',
                pid=None,
                status=HealthStatus.UNKNOWN,
                uptime=None,
                restart_count=0,
                last_restart=None,
                auto_restart=True,
                command=['python', 'social_listener.py']
            )
        }

        self.health_log = []
        self.last_checks = {}
        self.alert_thresholds = {
            'disk_space_gb': 1.0,  # Alert if less than 1GB
            'memory_percent': 90,   # Alert if > 90%
            'cpu_percent': 95       # Alert if > 95%
        }

    def run_health_check_cycle(self):
        """Run complete health check cycle"""

        # Check all processes
        self._check_processes()

        # Check system resources
        self._check_system_resources()

        # Check service health
        self._check_service_health()

        # Update dashboard
        self._update_dashboard()

        # Log health status
        self._log_health_status()

    def _check_processes(self):
        """Check if monitored processes are running"""

        for name, process_info in self.monitored_processes.items():
            try:
                # Find process by name
                pid = self._find_process_pid(name)

                if pid is None:
                    # Process not running
                    process_info.pid = None
                    process_info.status = HealthStatus.CRITICAL
                    process_info.uptime = None

                    # Auto-restart if enabled
                    if process_info.auto_restart:
                        self._restart_process(process_info)
                    else:
                        self._create_process_alert(process_info, "Process not running")
                else:
                    # Process is running
                    process_info.pid = pid
                    process_info.status = HealthStatus.HEALTHY

                    # Get uptime
                    proc = psutil.Process(pid)
                    process_info.uptime = datetime.now() - datetime.fromtimestamp(proc.create_time())

            except Exception as e:
                process_info.status = HealthStatus.UNKNOWN
                log_error(f"Failed to check process {name}: {str(e)}")

    def _find_process_pid(self, process_name: str) -> Optional[int]:
        """Find PID of process by name"""

        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if process_name in proc.info['name'] or process_name in cmdline:
                    return proc.info['pid']
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return None

    def _restart_process(self, process_info: ProcessInfo):
        """Restart a crashed process"""

        try:
            log_info(f"Restarting process: {process_info.name}")

            # Start the process
            subprocess.Popen(
                process_info.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=os.getcwd()
            )

            # Update process info
            process_info.restart_count += 1
            process_info.last_restart = datetime.now()

            # Create alert
            self._create_restart_alert(process_info)

            # Wait a bit and check if it started
            time.sleep(5)
            new_pid = self._find_process_pid(process_info.name)

            if new_pid:
                process_info.pid = new_pid
                process_info.status = HealthStatus.HEALTHY
                log_info(f"Successfully restarted {process_info.name} with PID {new_pid}")
            else:
                process_info.status = HealthStatus.CRITICAL
                log_error(f"Failed to restart {process_info.name}")

        except Exception as e:
            process_info.status = HealthStatus.CRITICAL
            log_error(f"Error restarting {process_info.name}: {str(e)}")
            self._create_process_alert(process_info, f"Restart failed: {str(e)}")

    def _check_system_resources(self):
        """Check system resource health"""

        # Disk space check
        disk_usage = psutil.disk_usage('/')
        free_gb = disk_usage.free / (1024**3)

        if free_gb < self.alert_thresholds['disk_space_gb']:
            self._handle_low_disk_space(free_gb)

        # Memory check
        memory = psutil.virtual_memory()
        if memory.percent > self.alert_thresholds['memory_percent']:
            self._create_resource_alert('memory', memory.percent)

        # CPU check
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent > self.alert_thresholds['cpu_percent']:
            self._create_resource_alert('cpu', cpu_percent)

    def _handle_low_disk_space(self, free_gb: float):
        """Handle low disk space situation"""

        # Create critical alert
        alert_data = {
            'type': 'disk_space_critical',
            'free_gb': free_gb,
            'timestamp': datetime.now().isoformat(),
            'action_taken': 'archiving_old_files'
        }

        self._create_health_alert('DISK_SPACE', alert_data)

        # Auto-archive old /Done files
        try:
            self._archive_old_done_files()
            log_info("Archived old /Done files to free disk space")
        except Exception as e:
            log_error(f"Failed to archive files: {str(e)}")

    def _archive_old_done_files(self):
        """Archive old files from /Done directory"""

        done_dir = "/Done"
        archive_dir = "/Archive"
        cutoff_date = datetime.now() - timedelta(days=30)

        os.makedirs(archive_dir, exist_ok=True)

        for file in os.listdir(done_dir):
            file_path = os.path.join(done_dir, file)
            if os.path.isfile(file_path):
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                if file_time < cutoff_date:
                    archive_path = os.path.join(archive_dir, file)
                    shutil.move(file_path, archive_path)
                    log_info(f"Archived {file} to {archive_dir}")

    def _check_service_health(self):
        """Check external service health"""

        # Check Odoo connection
        try:
            odoo_health = self._check_odoo_health()
            self._update_service_status('odoo', odoo_health)
        except Exception as e:
            self._update_service_status('odoo', {'status': 'error', 'message': str(e)})

        # Check API credentials
        try:
            api_health = self._check_api_credentials()
            self._update_service_status('api_credentials', api_health)
        except Exception as e:
            self._update_service_status('api_credentials', {'status': 'error', 'message': str(e)})

        # Check Obsidian vault
        try:
            vault_health = self._check_obsidian_vault()
            self._update_service_status('obsidian_vault', vault_health)
        except Exception as e:
            self._update_service_status('obsidian_vault', {'status': 'error', 'message': str(e)})

    def _check_odoo_health(self) -> Dict[str, Any]:
        """Check Odoo connection health"""

        try:
            # Test Odoo connection
            client = get_odoo_client()
            version = client.version()

            return {
                'status': 'healthy',
                'version': version,
                'response_time': 'fast'
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }

    def _check_api_credentials(self) -> Dict[str, Any]:
        """Check API credential validity"""

        credentials = {}

        # Check Gmail API
        try:
            gmail_valid = validate_gmail_credentials()
            credentials['gmail'] = 'valid' if gmail_valid else 'expired'
        except:
            credentials['gmail'] = 'error'

        # Check X/Twitter API
        try:
            twitter_valid = validate_twitter_credentials()
            credentials['twitter'] = 'valid' if twitter_valid else 'expired'
        except:
            credentials['twitter'] = 'error'

        # Check other APIs...

        # Overall status
        all_valid = all(status == 'valid' for status in credentials.values())

        return {
            'status': 'healthy' if all_valid else 'warning',
            'credentials': credentials
        }

    def _check_obsidian_vault(self) -> Dict[str, Any]:
        """Check Obsidian vault accessibility"""

        vault_path = "/Vault"

        try:
            # Check if vault directory exists
            if not os.path.exists(vault_path):
                return {'status': 'error', 'message': 'Vault directory not found'}

            # Test write access
            test_file = os.path.join(vault_path, '.health_check')
            with open(test_file, 'w') as f:
                f.write('health_check')
            os.remove(test_file)

            # Check vault lock
            lock_file = os.path.join(vault_path, '.obsidian/workspace.json')
            if os.path.exists(lock_file):
                # Try to read
                with open(lock_file, 'r') as f:
                    json.load(f)

            return {
                'status': 'healthy',
                'path': vault_path,
                'writable': True
            }

        except PermissionError:
            # Vault locked - write to /tmp/
            return self._handle_vault_locked()
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    def _handle_vault_locked(self) -> Dict[str, Any]:
        """Handle locked Obsidian vault"""

        tmp_path = "/tmp/vault_fallback"

        try:
            # Create fallback directory
            os.makedirs(tmp_path, exist_ok=True)

            # Schedule retry
            self._schedule_vault_retry()

            # Create alert
            alert_data = {
                'type': 'vault_locked',
                'fallback_path': tmp_path,
                'retry_interval': 30,
                'timestamp': datetime.now().isoformat()
            }

            self._create_health_alert('VAULT_LOCKED', alert_data)

            return {
                'status': 'warning',
                'message': 'Vault locked - using fallback',
                'fallback_path': tmp_path
            }

        except Exception as e:
            return {
                'status': 'critical',
                'message': f'Vault locked and fallback failed: {str(e)}'
            }

    def _schedule_vault_retry(self):
        """Schedule vault accessibility retry"""

        def retry_vault():
            while True:
                time.sleep(30)
                vault_health = self._check_obsidian_vault()
                if vault_health['status'] == 'healthy':
                    log_info("Obsidian vault is now accessible")
                    break

        # Run in background
        import threading
        retry_thread = threading.Thread(target=retry_vault, daemon=True)
        retry_thread.start()

    def _update_dashboard(self):
        """Update dashboard with health status"""

        try:
            dashboard_file = "Dashboard.md"

            # Generate health report section
            health_report = self._generate_health_report()

            # Update dashboard
            update_dashboard_section(dashboard_file, "System Health", health_report)

        except Exception as e:
            log_error(f"Failed to update dashboard: {str(e)}")

    def _generate_health_report(self) -> str:
        """Generate health report for dashboard"""

        now = datetime.now()
        report_lines = [
            f"## 🟢 System Health — {now.strftime('%Y-%m-%d %H:%M')}",
            "| Component         | Status  | Uptime    |",
            "|-------------------|---------|-----------|"
        ]

        # Process status
        for name, process_info in self.monitored_processes.items():
            status_icon = "✅ OK" if process_info.status == HealthStatus.HEALTHY else "⚠️ RESTARTED" if process_info.restart_count > 0 else "❌ DOWN"
            uptime_str = self._format_uptime(process_info.uptime) if process_info.uptime else "N/A"

            report_lines.append(
                f"| {name:<17} | {status_icon:<7} | {uptime_str:<9} |"
            )

        # System resources
        disk_usage = psutil.disk_usage('/')
        free_gb = disk_usage.free / (1024**3)
        disk_status = "✅" if free_gb >= 1 else "⚠️"

        memory = psutil.virtual_memory()
        memory_status = "✅" if memory.percent < 90 else "⚠️"

        report_lines.extend([
            f"| Disk Space        | {disk_status} {free_gb:.1f}GB free |      |",
            f"| Memory            | {memory_status} {memory.percent:.1f}% |      |"
        ])

        # Service health
        # (Add service status here based on checks)

        return "\n".join(report_lines)

    def _format_uptime(self, uptime: timedelta) -> str:
        """Format uptime for display"""

        if uptime is None:
            return "N/A"

        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, _ = divmod(remainder, 60)

        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"

    def _create_restart_alert(self, process_info: ProcessInfo):
        """Create alert for process restart"""

        alert_data = {
            'type': 'process_restart',
            'process': process_info.name,
            'restart_count': process_info.restart_count,
            'last_restart': process_info.last_restart.isoformat(),
            'auto_restart': process_info.auto_restart,
            'timestamp': datetime.now().isoformat()
        }

        self._create_health_alert('RESTART', alert_data)

    def _create_process_alert(self, process_info: ProcessInfo, message: str):
        """Create alert for process issue"""

        alert_data = {
            'type': 'process_issue',
            'process': process_info.name,
            'status': process_info.status.value,
            'message': message,
            'auto_restart': process_info.auto_restart,
            'timestamp': datetime.now().isoformat()
        }

        self._create_health_alert('PROCESS', alert_data)

    def _create_resource_alert(self, resource_type: str, value: float):
        """Create alert for resource issue"""

        alert_data = {
            'type': 'resource_warning',
            'resource': resource_type,
            'value': value,
            'threshold': self.alert_thresholds[f'{resource_type}_percent'],
            'timestamp': datetime.now().isoformat()
        }

        self._create_health_alert('RESOURCE', alert_data)

    def _create_health_alert(self, alert_type: str, alert_data: Dict[str, Any]):
        """Create health alert file"""

        timestamp = datetime.now().strftime('%Y-%m-%d')
        alert_file = f"/Needs_Action/HEALTH_{alert_type}_{timestamp}.md"

        try:
            alert_content = self._format_alert(alert_type, alert_data)

            with open(alert_file, 'w') as f:
                f.write(alert_content)

            log_info(f"Created health alert: {alert_file}")

        except Exception as e:
            log_error(f"Failed to create alert file: {str(e)}")

    def _format_alert(self, alert_type: str, alert_data: Dict[str, Any]) -> str:
        """Format alert data into markdown"""

        content = f"""---
type: health_alert
alert_type: {alert_type}
timestamp: {alert_data['timestamp']}
priority: {"high" if alert_type in ["DISK_SPACE", "VAULT_LOCKED"] else "medium"}
---

# Health Alert - {alert_type.replace('_', ' ').title()} - {alert_data['timestamp'][:10]}

## Alert Details
- **Type:** {alert_type}
- **Timestamp:** {alert_data['timestamp']}
- **Priority:** {"High" if alert_type in ["DISK_SPACE", "VAULT_LOCKED"] else "Medium"}

## Information
"""

        # Add specific information based on alert type
        if alert_type == 'RESTART':
            content += f"""
- **Process:** {alert_data['process']}
- **Restart Count:** {alert_data['restart_count']}
- **Last Restart:** {alert_data['last_restart']}
- **Auto-Restart:** {alert_data['auto_restart']}
"""
        elif alert_type == 'DISK_SPACE':
            content += f"""
- **Free Space:** {alert_data['free_gb']:.2f} GB
- **Action Taken:** {alert_data['action_taken']}
"""
        elif alert_type == 'VAULT_LOCKED':
            content += f"""
- **Fallback Path:** {alert_data['fallback_path']}
- **Retry Interval:** {alert_data['retry_interval']} seconds
"""

        content += """

## Recommended Actions
- [ ] Review system logs for details
- [ ] Verify root cause of issue
- [ ] Monitor for recurrence
- [ ] Update thresholds if needed

## System Context
- **Total Processes:** {len(self.monitored_processes)}
- **Healthy Processes:** {len([p for p in self.monitored_processes.values() if p.status == HealthStatus.HEALTHY])}
- **Critical Issues:** {len([p for p in self.monitored_processes.values() if p.status == HealthStatus.CRITICAL])}

---
*Auto-generated by System Health Watchdog*
"""

        return content

    def _log_health_status(self):
        """Log current health status"""

        now = datetime.now()
        log_entry = {
            'timestamp': now.isoformat(),
            'processes': {},
            'system_resources': {
                'disk_free_gb': psutil.disk_usage('/').free / (1024**3),
                'memory_percent': psutil.virtual_memory().percent,
                'cpu_percent': psutil.cpu_percent(interval=1)
            },
            'services': {}  # Add service status here
        }

        # Add process status
        for name, process_info in self.monitored_processes.items():
            log_entry['processes'][name] = {
                'status': process_info.status.value,
                'pid': process_info.pid,
                'uptime_seconds': process_info.uptime.total_seconds() if process_info.uptime else None,
                'restart_count': process_info.restart_count
            }

        # Write to log file
        log_file = f"/Logs/health_{now.strftime('%Y-%m-%d')}.json"

        try:
            # Read existing log
            logs = []
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    logs = json.load(f)

            # Add new entry
            logs.append(log_entry)

            # Keep only last 24 hours of logs
            cutoff = now - timedelta(hours=24)
            logs = [log for log in logs if datetime.fromisoformat(log['timestamp']) > cutoff]

            # Write back
            with open(log_file, 'w') as f:
                json.dump(logs, f, indent=2)

        except Exception as e:
            log_error(f"Failed to write health log: {str(e)}")

# Global watchdog instance
system_watchdog = SystemHealthWatchdog()
```

## Commands Reference

### Health Monitoring Commands
```bash
# Run immediate health check
/health-check

# Check specific process
/health-check --process orchestrator

# Check system resources
/health-check --resources

# Check service health
/health-check --services

# Generate full report
/health-report
```

### Process Management Commands
```bash
# Restart specific process
/health-restart --process gmail_watcher

# View process status
/health-status --process all

# Check restart history
/health-restart-history

# Enable/disable auto-restart
/health-auto-restart --process orchestrator --enable
```

### System Resource Commands
```bash
# Check disk usage
/health-disk

# Check memory usage
/health-memory

# Check CPU usage
/health-cpu

# Archive old files manually
/health-archive --days 30
```

### Alert Management Commands
```bash
# List active alerts
/health-alerts --active

# Acknowledge alert
/health-acknowledge --alert DISK_SPACE_2024-01-21

# Clear alert
/health-clear --alert RESTART_2024-01-21

# Alert history
/health-alerts --history --period 24h
```

## Integration Examples

### Integration with Other Skills
```python
# Wrapper for service calls with health check
def with_health_check(service_name: str, func: Callable):
    """Execute function with health check"""

    # Check service health first
    if service_name in system_watchdog.monitored_processes:
        process_info = system_watchdog.monitored_processes[service_name]
        if process_info.status != HealthStatus.HEALTHY:
            log_warning(f"Service {service_name} not healthy")
            return None

    # Execute function
    try:
        return func()
    except Exception as e:
        # Log error and trigger health check
        log_error(f"Service {service_name} error: {str(e)}")
        system_watchdog.run_health_check_cycle()
        raise
```

### Auto-Healing Integration
```python
def auto_heal_service(service_name: str):
    """Auto-heal a service"""

    process_info = system_watchdog.monitored_processes.get(service_name)
    if process_info and process_info.auto_restart:
        system_watchdog._restart_process(process_info)
        return True
    return False
```

## Best Practices

1. **Regular Monitoring**: Keep health checks running continuously
2. **Appropriate Thresholds**: Set thresholds based on system capacity
3. **Alert Responsiveness**: Respond to alerts promptly
4. **Log Analysis**: Review health logs for patterns
5. **Preventive Maintenance**: Address issues before they become critical
6. **Backup Strategies**: Maintain backups for critical failures

## Troubleshooting

### Common Issues
1. **"Process constantly restarting"**
   - Check process logs for errors
   - Verify dependencies are met
   - Review resource constraints

2. **"False health alerts"**
   - Adjust health check thresholds
   - Review check intervals
   - Verify monitoring logic

3. **"Dashboard not updating"**
   - Check file permissions
   - Verify dashboard file path
   - Review update logic

4. **"Auto-heal not working"**
   - Check process commands
   - Verify permissions
   - Review restart logic

## Security Considerations

1. **Process Permissions**: Run processes with appropriate permissions
2. **Log Access**: Restrict access to health logs
3. **Alert Sensitivity**: Avoid exposing sensitive information in alerts
4. **Auto-Restart Security**: Validate process before restarting
5. **Resource Monitoring**: Don't expose system details in alerts