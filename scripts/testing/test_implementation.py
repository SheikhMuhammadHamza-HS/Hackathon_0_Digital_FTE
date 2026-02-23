
#!/usr/bin/env python3
"""
Comprehensive Implementation Test Suite
Tests all Phase 7 polish tasks to ensure perfect functionality
"""

import asyncio
import json
import time
import sqlite3
import tempfile
import shutil
import subprocess
import requests
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ImplementationTester:
    """Comprehensive test suite for AI Employee implementation"""

    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.test_results = []
        self.api_base = "http://localhost:8000"
        self.auth_token = None

    def log_test(self, test_name: str, status: str, message: str, details: Dict = None):
        """Log test result"""
        result = {
            "test": test_name,
            "status": status,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        self.test_results.append(result)

        icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{icon} {test_name}: {message}")

        if details:
            for key, value in details.items():
                print(f"   - {key}: {value}")

    async def run_all_tests(self):
        """Run comprehensive test suite"""
        print("="*60)
        print("AI Employee Implementation Test Suite")
        print("="*60)
        print(f"Started at: {datetime.now().isoformat()}")
        print()

        # Test categories
        await self.test_error_handling()
        await self.test_performance_optimization()
        await self.test_security_hardening()
        await self.test_data_retention()
        await self.test_gdpr_compliance()
        await self.test_monitoring_dashboard()
        await self.test_backup_restore()
        await self.test_documentation()

        # Generate report
        self.generate_report()

        return self.get_overall_status()

    async def test_error_handling(self):
        """Test T075 - Error handling implementation"""
        print("\n🔧 Testing Error Handling Implementation")
        print("-" * 40)

        # Test 1: Custom error classes exist
        try:
            from ai_employee.utils.error_handlers import (
                AIEmployeeError,
                ConfigurationError,
                ValidationError,
                IntegrationError
            )
            self.log_test(
                "Error Classes",
                "PASS",
                "All custom error classes imported successfully"
            )
        except ImportError as e:
            self.log_test(
                "Error Classes",
                "FAIL",
                f"Failed to import error classes: {e}"
            )

        # Test 2: Error handling middleware
        try:
            from ai_employee.api.server import app
            # Test non-existent endpoint
            response = requests.get(f"{self.api_base}/api/v1/nonexistent", timeout=5)
            if response.status_code == 404:
                self.log_test(
                    "404 Error Handling",
                    "PASS",
                    "Proper 404 response returned"
                )
            else:
                self.log_test(
                    "404 Error Handling",
                    "FAIL",
                    f"Expected 404, got {response.status_code}"
                )
        except Exception as e:
            self.log_test(
                "404 Error Handling",
                "FAIL",
                f"Error testing 404: {e}"
            )

        # Test 3: Validation error handling
        try:
            response = requests.post(
                f"{self.api_base}/api/v1/clients",
                json={"name": "", "email": "invalid-email"},  # Invalid data
                timeout=5
            )
            if response.status_code in [400, 422]:
                self.log_test(
                    "Validation Error",
                    "PASS",
                    "Validation errors properly handled"
                )
            else:
                self.log_test(
                    "Validation Error",
                    "FAIL",
                    f"Expected validation error, got {response.status_code}"
                )
        except Exception as e:
            self.log_test(
                "Validation Error",
                "FAIL",
                f"Error testing validation: {e}"
            )

    async def test_performance_optimization(self):
        """Test T076 - Performance optimization"""
        print("\n⚡ Testing Performance Optimization")
        print("-" * 40)

        # Test 1: Cache manager exists
        try:
            from ai_employee.utils.performance import CacheManager
            cache = CacheManager()
            self.log_test(
                "Cache Manager",
                "PASS",
                "Cache manager initialized"
            )

            # Test cache operations
            await cache.set("test_key", "test_value", ttl=60)
            value = await cache.get("test_key")
            if value == "test_value":
                self.log_test(
                    "Cache Operations",
                    "PASS",
                    "Cache set/get working"
                )
            else:
                self.log_test(
                    "Cache Operations",
                    "FAIL",
                    "Cache returned wrong value"
                )
        except Exception as e:
            self.log_test(
                "Cache Manager",
                "FAIL",
                f"Cache manager error: {e}"
            )

        # Test 2: Performance monitor
        try:
            from ai_employee.utils.performance import performance_monitor
            # Test performance measurement
            with performance_monitor.measure("test_operation"):
                time.sleep(0.1)

            metrics = performance_monitor.get_metrics("test_operation")
            if metrics and len(metrics) > 0:
                self.log_test(
                    "Performance Monitor",
                    "PASS",
                    f"Captured {len(metrics)} metrics"
                )
            else:
                self.log_test(
                    "Performance Monitor",
                    "FAIL",
                    "No metrics captured"
                )
        except Exception as e:
            self.log_test(
                "Performance Monitor",
                "FAIL",
                f"Performance monitor error: {e}"
            )

    async def test_security_hardening(self):
        """Test T078 - Security hardening"""
        print("\n🔒 Testing Security Hardening")
        print("-" * 40)

        # Test 1: JWT authentication
        try:
            from ai_employee.utils.security import TokenManager
            token_manager = TokenManager()

            # Test token creation
            token = token_manager.create_access_token({"user_id": "test"})
            if token:
                self.log_test(
                    "JWT Token Creation",
                    "PASS",
                    "Token created successfully"
                )

                # Test token validation
                payload = token_manager.verify_token(token)
                if payload and payload.get("user_id") == "test":
                    self.log_test(
                        "JWT Token Validation",
                        "PASS",
                        "Token validated successfully"
                    )
                else:
                    self.log_test(
                        "JWT Token Validation",
                        "FAIL",
                        "Token validation failed"
                    )
            else:
                self.log_test(
                    "JWT Token Creation",
                    "FAIL",
                    "Failed to create token"
                )
        except Exception as e:
            self.log_test(
                "JWT Authentication",
                "FAIL",
                f"JWT error: {e}"
            )

        # Test 2: Rate limiting
        try:
            from ai_employee.utils.security import RateLimiter
            limiter = RateLimiter(max_requests=5, window_seconds=60)

            # Test rate limiting
            success_count = 0
            for i in range(7):
                if limiter.is_allowed("test_ip"):
                    success_count += 1

            if success_count <= 5:
                self.log_test(
                    "Rate Limiting",
                    "PASS",
                    f"Rate limiting working (allowed {success_count}/7)"
                )
            else:
                self.log_test(
                    "Rate Limiting",
                    "FAIL",
                    f"Rate limiting failed (allowed {success_count}/7)"
                )
        except Exception as e:
            self.log_test(
                "Rate Limiting",
                "FAIL",
                f"Rate limiter error: {e}"
            )

        # Test 3: Input validation
        try:
            from ai_employee.utils.security import InputValidator
            validator = InputValidator()

            # Test XSS prevention
            xss_input = "<script>alert('xss')</script>"
            sanitized = validator.sanitize_input(xss_input)
            if "<script>" not in sanitized:
                self.log_test(
                    "XSS Prevention",
                    "PASS",
                    "XSS input sanitized"
                )
            else:
                self.log_test(
                    "XSS Prevention",
                    "FAIL",
                    "XSS not sanitized"
                )
        except Exception as e:
            self.log_test(
                "Input Validation",
                "FAIL",
                f"Validator error: {e}"
            )

    async def test_data_retention(self):
        """Test T079 - Data retention automation"""
        print("\n📅 Testing Data Retention")
        print("-" * 40)

        # Test 1: Data retention manager
        try:
            from ai_employee.utils.data_retention import DataRetentionManager
            retention_manager = DataRetentionManager()

            # Test policy creation
            policy = retention_manager.create_policy(
                name="test_policy",
                retention_days=30,
                action="anonymize",
                data_type="user_data"
            )

            if policy:
                self.log_test(
                    "Retention Policy Creation",
                    "PASS",
                    "Policy created successfully"
                )
            else:
                self.log_test(
                    "Retention Policy Creation",
                    "FAIL",
                    "Failed to create policy"
                )
        except Exception as e:
            self.log_test(
                "Data Retention Manager",
                "FAIL",
                f"Retention manager error: {e}"
            )

        # Test 2: Retention execution
        try:
            from ai_employee.utils.retention_scheduler import retention_task_manager

            # Test task scheduling
            task_id = await retention_task_manager.schedule_retention_task(
                policy_name="test_policy",
                schedule_type="daily"
            )

            if task_id:
                self.log_test(
                    "Retention Scheduling",
                    "PASS",
                    f"Task scheduled: {task_id}"
                )
            else:
                self.log_test(
                    "Retention Scheduling",
                    "FAIL",
                    "Failed to schedule task"
                )
        except Exception as e:
            self.log_test(
                "Retention Scheduling",
                "FAIL",
                f"Scheduling error: {e}"
            )

    async def test_gdpr_compliance(self):
        """Test T080 - GDPR compliance"""
        print("\n🇪🇺 Testing GDPR Compliance")
        print("-" * 40)

        # Test 1: GDPR manager
        try:
            from ai_employee.utils.gdpr import GDPRManager
            gdpr_manager = GDPRManager()

            # Test data subject creation
            subject = await gdpr_manager.register_data_subject(
                identifier="test@example.com",
                identifier_type="email",
                name="Test User",
                jurisdiction="EU"
            )

            if subject and subject.id:
                self.log_test(
                    "Data Subject Registration",
                    "PASS",
                    f"Subject registered: {subject.id}"
                )

                # Test consent recording
                consent = await gdpr_manager.record_consent(
                    subject_id=subject.id,
                    purpose="marketing",
                    granted=True,
                    legal_basis="consent"
                )

                if consent:
                    self.log_test(
                        "Consent Recording",
                        "PASS",
                        "Consent recorded successfully"
                    )
                else:
                    self.log_test(
                        "Consent Recording",
                        "FAIL",
                        "Failed to record consent"
                    )
            else:
                self.log_test(
                    "Data Subject Registration",
                    "FAIL",
                    "Failed to register subject"
                )
        except Exception as e:
            self.log_test(
                "GDPR Manager",
                "FAIL",
                f"GDPR manager error: {e}"
            )

        # Test 2: Right to access
        try:
            if 'subject' in locals():
                access_data = await gdpr_manager.get_subject_data(subject.id)
                if access_data is not None:
                    self.log_test(
                        "Right to Access",
                        "PASS",
                        "Data access granted"
                    )
                else:
                    self.log_test(
                        "Right to Access",
                        "FAIL",
                        "Data access denied"
                    )
        except Exception as e:
            self.log_test(
                "Right to Access",
                "FAIL",
                f"Access error: {e}"
            )

    async def test_monitoring_dashboard(self):
        """Test T081 - Monitoring dashboard"""
        print("\n📊 Testing Monitoring Dashboard")
        print("-" * 40)

        # Test 1: Monitoring dashboard files
        dashboard_files = [
            "ai_employee/web/dashboard/index.html",
            "ai_employee/web/dashboard/dashboard.css",
            "ai_employee/web/dashboard/dashboard.js"
        ]

        all_files_exist = True
        for file_path in dashboard_files:
            full_path = self.base_dir / file_path
            if full_path.exists():
                size = full_path.stat().st_size
                self.log_test(
                    f"Dashboard File: {Path(file_path).name}",
                    "PASS",
                    f"Exists ({size} bytes)"
                )
            else:
                self.log_test(
                    f"Dashboard File: {Path(file_path).name}",
                    "FAIL",
                    "File not found"
                )
                all_files_exist = False

        # Test 2: Monitoring utilities
        try:
            from ai_employee.utils.monitoring import MonitoringDashboard
            monitor = MonitoringDashboard()

            # Test metric collection
            await monitor.collect_system_metrics()
            metrics = monitor.get_metrics_summary()

            if metrics and "cpu" in metrics:
                self.log_test(
                    "Metric Collection",
                    "PASS",
                    f"Collected metrics: {list(metrics.keys())}"
                )
            else:
                self.log_test(
                    "Metric Collection",
                    "FAIL",
                    "No metrics collected"
                )
        except Exception as e:
            self.log_test(
                "Monitoring Dashboard",
                "FAIL",
                f"Monitoring error: {e}"
            )

        # Test 3: API endpoints
        try:
            # Test health endpoint
            response = requests.get(f"{self.api_base}/api/v1/monitoring/health", timeout=5)
            if response.status_code == 200:
                self.log_test(
                    "Monitoring Health Endpoint",
                    "PASS",
                    "Health endpoint responding"
                )
            else:
                self.log_test(
                    "Monitoring Health Endpoint",
                    "FAIL",
                    f"Status: {response.status_code}"
                )
        except Exception as e:
            self.log_test(
                "Monitoring Health Endpoint",
                "FAIL",
                f"Endpoint error: {e}"
            )

    async def test_backup_restore(self):
        """Test T082 - Backup and restore procedures"""
        print("\n💾 Testing Backup and Restore")
        print("-" * 40)

        # Test 1: Backup manager
        try:
            from ai_employee.utils.backup_manager import BackupManager

            # Create temporary backup directory
            temp_dir = Path(tempfile.mkdtemp())

            # Mock config
            class MockConfig:
                BACKUP_DIRECTORY = str(temp_dir / "backups")
                DATABASE_PATH = str(temp_dir / "test.db")

            import ai_employee.utils.backup_manager
            original_config = ai_employee.utils.backup_manager.Config
            ai_employee.utils.backup_manager.Config = MockConfig

            backup_manager = BackupManager()

            # Test backup creation
            result = await backup_manager.create_backup(
                backup_type="test",
                include_media=False,
                encrypt=False
            )

            if result["status"] == "success":
                self.log_test(
                    "Backup Creation",
                    "PASS",
                    f"Backup created: {result['backup_id']}"
                )

                # Test backup listing
                backups = await backup_manager.list_backups()
                if len(backups) > 0:
                    self.log_test(
                        "Backup Listing",
                        "PASS",
                        f"Found {len(backups)} backups"
                    )

                    # Test backup verification
                    verification = await backup_manager.verify_backup(result["backup_id"])
                    if verification["status"] == "success":
                        self.log_test(
                            "Backup Verification",
                            "PASS",
                            "Backup integrity verified"
                        )
                    else:
                        self.log_test(
                            "Backup Verification",
                            "FAIL",
                            verification.get("message", "Unknown error")
                        )
                else:
                    self.log_test(
                        "Backup Listing",
                        "FAIL",
                        "No backups found"
                    )
            else:
                self.log_test(
                    "Backup Creation",
                    "FAIL",
                    result.get("message", "Unknown error")
                )

            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)
            ai_employee.utils.backup_manager.Config = original_config

        except Exception as e:
            self.log_test(
                "Backup Manager",
                "FAIL",
                f"Backup error: {e}"
            )

        # Test 2: Backup API endpoints
        try:
            # Test backup statistics
            response = requests.get(f"{self.api_base}/api/v1/backup/statistics", timeout=5)
            if response.status_code == 200:
                self.log_test(
                    "Backup Statistics API",
                    "PASS",
                    "Statistics endpoint working"
                )
            else:
                self.log_test(
                    "Backup Statistics API",
                    "FAIL",
                    f"Status: {response.status_code}"
                )
        except Exception as e:
            self.log_test(
                "Backup Statistics API",
                "FAIL",
                f"API error: {e}"
            )

    async def test_documentation(self):
        """Test documentation completeness"""
        print("\n📚 Testing Documentation")
        print("-" * 40)

        # Required documentation files
        required_docs = [
            ("docs/deployment_guide.md", "Deployment Guide"),
            ("docs/docker_deployment.md", "Docker Deployment"),
            ("docs/aws_deployment.md", "AWS Deployment"),
            ("docs/backup_and_restore.md", "Backup Guide"),
            ("docs/gdpr_compliance.md", "GDPR Guide"),
            ("docs/security_hardening.md", "Security Guide"),
            ("docs/deployment_checklist.md", "Deployment Checklist"),
            ("specs/001-ai-employee/quickstart.md", "Quickstart Guide")
        ]

        for doc_path, doc_name in required_docs:
            full_path = self.base_dir / doc_path
            if full_path.exists():
                size = full_path.stat().st_size
                lines = len(full_path.read_text(encoding='utf-8').split('\n'))
                self.log_test(
                    f"Documentation: {doc_name}",
                    "PASS",
                    f"Exists ({size} bytes, {lines} lines)"
                )
            else:
                self.log_test(
                    f"Documentation: {doc_name}",
                    "FAIL",
                    "File not found"
                )

    def generate_report(self):
        """Generate comprehensive test report"""
        print("\n" + "="*60)
        print("TEST REPORT SUMMARY")
        print("="*60)

        total_tests = len(self.test_results)
        passed = sum(1 for r in self.test_results if r["status"] == "PASS")
        failed = sum(1 for r in self.test_results if r["status"] == "FAIL")
        warnings = sum(1 for r in self.test_results if r["status"] == "WARN")

        print(f"\nTotal Tests: {total_tests}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️  Warnings: {warnings}")

        pass_rate = (passed / total_tests * 100) if total_tests > 0 else 0
        print(f"Success Rate: {pass_rate:.1f}%")

        if failed == 0:
            print("\n🎉 ALL TESTS PASSED!")
            print("The implementation is working perfectly!")
        else:
            print(f"\n⚠️  {failed} TESTS FAILED")
            print("Please review and fix the failed tests.")

        # Save detailed report
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": total_tests,
                "passed": passed,
                "failed": failed,
                "warnings": warnings,
                "pass_rate": pass_rate
            },
            "results": self.test_results
        }

        report_file = self.base_dir / "test_report.json"
        with open(report_file, "w") as f:
            json.dump(report_data, f, indent=2)

        print(f"\nDetailed report saved to: {report_file}")

        # Show failed tests
        if failed > 0:
            print("\nFailed Tests:")
            for result in self.test_results:
                if result["status"] == "FAIL":
                    print(f"  ❌ {result['test']}: {result['message']}")

    def get_overall_status(self) -> bool:
        """Get overall test status"""
        failed = sum(1 for r in self.test_results if r["status"] == "FAIL")
        return failed == 0

async def main():
    """Main test runner"""
    # Set environment variables
    os.environ["SECRET_KEY"] = "test-secret-key-for-testing-12chars"
    os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-for-testing-12chars"
    os.environ["ENVIRONMENT"] = "test"

    # Run tests
    tester = ImplementationTester()
    success = await tester.run_all_tests()

    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)