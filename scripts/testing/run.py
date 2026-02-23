#!/usr/bin/env python3
"""
Testing Runner
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment
env_file = project_root / "scripts" / "config" / ".env"
if env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(env_file)

# Import and run
if __name__ == "__main__":
    test_file = sys.argv[1] if len(sys.argv) > 1 else "help"

    if test_file == "core":
        from test_core_final import main
        main()
    elif test_file == "invoice":
        from test_invoice_workflow import main
        main()
    elif test_file == "approval":
        from test_approval_detection import main
        import asyncio
        asyncio.run(main())
    elif test_file == "simple":
        from simple_test import main
        main()
    else:
        print("Available tests:")
        print("  python run.py core      - Core modules test")
        print("  python run.py invoice   - Invoice workflow test")
        print("  python run.py approval  - Approval detection test")
        print("  python run.py simple    - Simple verification test")