#!/usr/bin/env python3
"""
Odoo Test Runner
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
    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            from test_odoo_real import main
            import asyncio
            asyncio.run(main())
        elif sys.argv[1] == "setup":
            from configure_odoo_real import main
            main()
        elif sys.argv[1] == "update":
            from update_odoo_credentials import main
            main()
    else:
        print("Usage: python run.py [test|setup|update]")