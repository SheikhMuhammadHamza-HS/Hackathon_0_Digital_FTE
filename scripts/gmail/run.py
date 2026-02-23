#!/usr/bin/env python3
"""
Gmail Test Runner
"""
import sys
import os
import asyncio
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
        if sys.argv[1] == "agent":
            from run_gmail_agent import main
            asyncio.run(main())
        elif sys.argv[1] == "debug":
            from debug_gmail_send import main
            main()
        elif sys.argv[1] == "refresh":
            from refresh_gmail_token import main
            main()
        elif sys.argv[1] == "send":
            from send_approved_email import send_email
            send_email()
    else:
        print("Usage: python run.py [agent|debug|refresh]")