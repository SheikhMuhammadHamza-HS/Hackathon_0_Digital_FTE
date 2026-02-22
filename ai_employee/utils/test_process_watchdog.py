"""
Test script for process watchdog system.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.process_watchdog import ProcessWatchdog, ProcessStatus, RestartStrategy, HealthCheckType
from utils.logging_config import configure_logging


async def test_process_registration():
    """Test process registration."""
    print("\n=== Testing Process Registration ===")

    watchdog = ProcessWatchdog()
    await watchdog.initialize()

    # Register a simple process (echo server)
    process_info = await watchdog.register_process(
        name="test_echo",
        command=["python", "-c", """
import time
while True:
    print('heartbeat')
    time.sleep(2)
        """],
        auto_restart=True,
        restart_strategy=RestartStrategy.EXPONENTIAL_BACKOFF,
        max_restarts=3,
        health_checks=[HealthCheckType.HEARTBEAT, HealthCheckType.CPU_USAGE]
    )

    print(f"Registered process: {process_info.name}")
    print(f"Command: {' '.join(process_info.command)}")
    print(f"Auto restart: {process_info.auto_restart}")
    print(f"Restart strategy: {process_info.restart_strategy}")

    # Start the process
    success = await watchdog.start_process("test_echo")
    print(f"Process started: {success}")

    # Wait a bit
    await asyncio.sleep(5)

    # Check status
    status = await watchdog.get_process_status("test_echo")
    print(f"Process status: {status.status}")
    print(f"PID: {status.pid}")
    print(f"Uptime: {status.uptime:.2f}s")

    # Stop the process
    success = await watchdog.stop_process("test_echo")
    print(f"Process stopped: {success}")

    await watchdog.shutdown()


async def test_restart_backoff():
    """Test restart backoff strategies."""
    print("\n=== Testing Restart Backoff ===")

    watchdog = ProcessWatchdog()
    await watchdog.initialize()

    # Register a process that exits immediately
    process_info = await watchdog.register_process(
        name="test_fail",
        command=["python", "-c", "print('exiting'); exit(1)"],
        auto_restart=True,
        restart_strategy=RestartStrategy.LINEAR_BACKOFF,
        max_restarts=3,
        health_checks=[HealthCheckType.HEARTBEAT]
    )

    print(f"Registered failing process: {process_info.name}")

    # Start the process (it will fail and restart)
    success = await watchdog.start_process("test_fail")
    print(f"Process started: {success}")

    # Wait for restarts
    await asyncio.sleep(10)

    # Check restart history
    history = await watchdog.get_restart_history("test_fail")
    print(f"Restart attempts: {len(history)}")
    for h in history[-3:]:
        print(f"  - {h.timestamp}: {h.reason} (successful: {h.successful})")

    await watchdog.shutdown()


async def test_health_checks():
    """Test health checking."""
    print("\n=== Testing Health Checks ===")

    watchdog = ProcessWatchdog()
    await watchdog.initialize()

    # Register a process with health checks
    process_info = await watchdog.register_process(
        name="test_health",
        command=["python", "-c", """
import time
import random
while True:
    # Simulate variable load
    if random.random() < 0.1:
        time.sleep(1)  # Simulate CPU spike
    else:
        time.sleep(0.1)
        """],
        auto_restart=False,
        health_checks=[
            HealthCheckType.HEARTBEAT,
            HealthCheckType.CPU_USAGE,
            HealthCheckType.MEMORY_USAGE
        ]
    )

    # Start the process
    await watchdog.start_process("test_health")

    # Monitor for a while
    for i in range(10):
        status = await watchdog.get_process_status("test_health")
        print(f"Iteration {i+1}: CPU={status.cpu_percent:.1f}%, Memory={status.memory_mb:.1f}MB")
        await asyncio.sleep(2)

    # Stop the process
    await watchdog.stop_process("test_health")

    await watchdog.shutdown()


async def test_multiple_processes():
    """Test monitoring multiple processes."""
    print("\n=== Testing Multiple Processes ===")

    watchdog = ProcessWatchdog()
    await watchdog.initialize()

    # Register multiple processes
    processes = [
        {
            "name": "worker_1",
            "command": ["python", "-c", "import time; time.sleep(30)"],
            "restart_strategy": RestartStrategy.IMMEDIATE
        },
        {
            "name": "worker_2",
            "command": ["python", "-c", "import time; time.sleep(30)"],
            "restart_strategy": RestartStrategy.EXPONENTIAL_BACKOFF
        },
        {
            "name": "service_1",
            "command": ["python", "-c", "import time; print('service running'); time.sleep(30)"],
            "restart_strategy": RestartStrategy.FIXED_INTERVAL
        }
    ]

    for proc in processes:
        await watchdog.register_process(**proc)
        await watchdog.start_process(proc["name"])

    # Monitor all processes
    for i in range(5):
        all_processes = await watchdog.get_all_processes()
        print(f"\n--- Status Check {i+1} ---")
        for name, info in all_processes.items():
            print(f"{name}: status={info.status.value}, pid={info.pid}")
        await asyncio.sleep(2)

    # Get statistics
    stats = watchdog.get_statistics()
    print(f"\nStatistics: {stats}")

    # Clean up
    for proc in processes:
        await watchdog.stop_process(proc["name"])

    await watchdog.shutdown()


async def main():
    """Run all tests."""
    configure_logging()

    print("Testing Process Watchdog System")
    print("=" * 50)

    try:
        await test_process_registration()
        await test_restart_backoff()
        await test_health_checks()
        await test_multiple_processes()
    except Exception as e:
        print(f"Test error: {e}")
        import traceback
        traceback.print_exc()

    print("\nTesting complete!")


if __name__ == "__main__":
    asyncio.run(main())