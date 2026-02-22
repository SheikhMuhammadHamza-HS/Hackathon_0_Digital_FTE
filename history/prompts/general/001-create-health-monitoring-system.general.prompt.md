---
ID: 001
TITLE: Create health monitoring system
STAGE: general
DATE_ISO: 2026-02-21
SURFACE: agent
MODEL: claude-opus-4-6
FEATURE: health_monitoring
BRANCH: 001-silver-tier-ai
USER: user
COMMAND: create_health_monitor_system
LABELS: ["health_monitoring", "system_monitoring", "metrics", "alerts"]
LINKS:
  SPEC: null
  TICKET: "T039"
  ADR: null
  PR: null
FILES_YAML:
  - ai_employee/utils/health_monitor.py
  - ai_employee/api/health_endpoints.py
  - ai_employee/utils/test_health_monitor.py
  - docs/health_monitoring.md
  - ai_employee/requirements.txt
TESTS_YAML:
  - ai_employee/utils/test_health_monitor.py
PROMPT_TEXT: |
  I need to create a comprehensive health monitoring system in ai_employee/utils/health_monitor.py as specified in task T039. Based on the existing patterns and requirements, the system should:

  1. Monitor system health metrics (CPU, memory, disk space)
  2. Track service availability and response times
  3. Detect anomalies and performance degradation
  4. Generate health status reports
  5. Integrate with the error recovery system
  6. Support configurable health checks and thresholds
  7. Provide health status API endpoints

  The system should:
  - Use async/await patterns
  - Integrate with existing infrastructure (event bus, config)
  - Provide real-time monitoring capabilities
  - Support configurable thresholds and alerts
  - Generate health events for monitoring
  - Follow the established patterns in the codebase

  Please create ai_employee/utils/health_monitor.py with:
  - HealthMonitor class for system monitoring
  - HealthStatus model (if not already created)
  - Health check implementations for different components
  - Resource monitoring (CPU, memory, disk)
  - Service availability monitoring
  - Health event publishing
  - Background monitoring tasks
  - Integration with error recovery system

  Make sure to follow the existing code patterns and integrate properly with the event bus, config system, and other infrastructure components.
RESPONSE_TEXT: |
  Created a comprehensive health monitoring system with the following components:

  1. **Health Monitor Core** (`ai_employee/utils/health_monitor.py`):
     - HealthMonitor class with async/await patterns
     - HealthCheck, HealthMetric, HealthReport models
     - System resource monitoring (CPU, memory, disk)
     - Service availability checks
     - Alert management with severity levels
     - Background monitoring tasks
     - Integration with event bus

  2. **API Endpoints** (`ai_employee/api/health_endpoints.py`):
     - RESTful endpoints for health status
     - Metrics and alerts API
     - Kubernetes probes (liveness/readiness)
     - Check management endpoints

  3. **Integration with Error Recovery**:
     - Registered error rate, circuit breaker, and queue depth checks
     - Health events published for critical errors
     - Automatic health check triggers

  4. **Documentation** (`docs/health_monitoring.md`):
     - Comprehensive documentation
     - Usage examples
     - API reference
     - Best practices

  5. **Test Demo** (`ai_employee/utils/test_health_monitor.py`):
     - Demonstration script
     - Shows system capabilities
     - Custom check examples

  6. **Dependencies Updated**:
     - Added psutil and aiofiles to requirements.txt

  The system follows all existing patterns:
   - Uses event bus for publishing health events
   - Integrates with config system for settings
   - Uses structured logging
   - Follows async/await patterns throughout
   - Proper error handling and recovery
OUTCOME: Successfully implemented a comprehensive health monitoring system that meets all specified requirements and integrates seamlessly with the existing infrastructure.
EVALUATION: The implementation provides:
  - Real-time monitoring capabilities
  - Configurable thresholds and alerts
  - Comprehensive API endpoints
  - Integration with error recovery system
  - Performance optimizations
  - Extensible architecture for custom checks
  - Full documentation and examples
  - Production-ready features (probes, metrics history, alert management)
---