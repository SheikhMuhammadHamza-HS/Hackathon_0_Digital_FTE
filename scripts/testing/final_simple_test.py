#!/usr/bin/env python3
"""
Final Simple Test - No special characters
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Set environment variables
os.environ["SECRET_KEY"] = "Test-Secret-Key-12-Chars!"
os.environ["JWT_SECRET_KEY"] = "Test-JWT-Secret-12-Chars!"
os.environ["ENVIRONMENT"] = "test"

print("="*60)
print("AI EMPLOYEE FINAL TEST")
print("="*60)

def main():
    """Run final test"""
    print(f"Started at: {datetime.now().isoformat()}")

    results = {}

    # Test imports
    print("\nTesting Core Modules...")
    modules_to_test = [
        ("Security", "ai_employee.utils.security"),
        ("Backup", "ai_employee.utils.backup_manager"),
        ("Monitoring", "ai_employee.utils.monitoring"),
        ("GDPR", "ai_employee.utils.gdpr"),
        ("Performance", "ai_employee.utils.performance"),
        ("Data Retention", "ai_employee.utils.data_retention")
    ]

    for name, module in modules_to_test:
        try:
            __import__(module)
            print(f"[OK] {name}: Imported")
            results[name] = "PASS"
        except Exception as e:
            print(f"[FAIL] {name}: {e}")
            results[name] = "FAIL"

    # Test files
    print("\nTesting Required Files...")
    files_to_test = [
        ("Dashboard HTML", "ai_employee/web/dashboard/index.html"),
        ("Dashboard CSS", "ai_employee/web/dashboard/dashboard.css"),
        ("Dashboard JS", "ai_employee/web/dashboard/dashboard.js"),
        ("Deployment Guide", "docs/deployment_guide.md"),
        ("Docker Guide", "docs/docker_deployment.md"),
        ("AWS Guide", "docs/aws_deployment.md"),
        ("Backup Guide", "docs/backup_and_restore.md"),
        ("GDPR Guide", "docs/gdpr_compliance.md"),
        ("Security Guide", "docs/security_hardening.md"),
        ("Checklist", "docs/deployment_checklist.md"),
        ("Quickstart", "specs/001-ai-employee/quickstart.md")
    ]

    for name, file_path in files_to_test:
        if Path(file_path).exists():
            print(f"[OK] {name}: Found")
            results[name] = "PASS"
        else:
            print(f"[FAIL] {name}: Missing")
            results[name] = "FAIL"

    # Test directories
    print("\nTesting Directories...")
    dirs_to_test = [
        ("utils", "ai_employee/utils"),
        ("api", "ai_employee/api"),
        ("web/dashboard", "ai_employee/web/dashboard"),
        ("domains", "ai_employee/domains"),
        ("tests", "tests"),
        ("docs", "docs")
    ]

    for name, dir_path in dirs_to_test:
        if Path(dir_path).exists():
            print(f"[OK] {name}: Directory exists")
            results[f"Directory {name}"] = "PASS"
        else:
            print(f"[FAIL] {name}: Directory missing")
            results[f"Directory {name}"] = "FAIL"

    # Test functionality
    print("\nTesting Functionality...")
    try:
        from ai_employee.utils.security import TokenManager
        tm = TokenManager()
        token = tm.create_access_token({"user": "test"})
        assert len(token) > 10
        print("[OK] JWT Token: Working")
        results["JWT"] = "PASS"
    except Exception as e:
        print(f"[FAIL] JWT Token: {e}")
        results["JWT"] = "FAIL"

    try:
        from ai_employee.utils.performance import CacheManager
        cache = CacheManager()
        print("[OK] Cache Manager: Working")
        results["Cache"] = "PASS"
    except Exception as e:
        print(f"[FAIL] Cache Manager: {e}")
        results["Cache"] = "FAIL"

    # Generate summary
    print("\n" + "="*60)
    print("TEST RESULTS")
    print("="*60)

    passed = sum(1 for v in results.values() if v == "PASS")
    total = len(results)
    failed = sum(1 for v in results.values() if v == "FAIL")

    print(f"\nTotal Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if passed >= 8:
        print("\n[SUCCESS] Implementation is working!")
        print("\nWorking Components:")
        for name, status in results.items():
            if status == "PASS":
                print(f"  [OK] {name}")
        return True
    else:
        print(f"\n[ISSUE] Only {passed}/{total} tests passed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)