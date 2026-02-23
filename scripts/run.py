#!/usr/bin/env python3
"""
Main Script Runner - AI Employee System
"""
import sys
from pathlib import Path

def main():
    """Main runner"""
    print("="*60)
    print("AI Employee - Script Runner")
    print("="*60)

    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python run.py <service> <command>")
        print("\nServices:")
        print("  odoo      - Odoo ERP integration")
        print("  gmail     - Gmail API integration")
        print("  testing   - Test suites")
        print("  config    - Configuration management")
        print("\nExamples:")
        print("  python run.py odoo test")
        print("  python run.py gmail agent")
        print("  python run.py testing core")
        print("  python run.py config setup")
        return

    service = sys.argv[1]
    command = sys.argv[2] if len(sys.argv) > 2 else None

    service_path = Path(__file__).parent / service

    if not service_path.exists():
        print(f"[ERROR] Service '{service}' not found")
        return

    run_script = service_path / "run.py"

    if not run_script.exists():
        print(f"[ERROR] No run.py found for '{service}'")
        return

    # Run the service using subprocess
    import subprocess

    if service == "odoo":
        if command:
            subprocess.run([sys.executable, "run.py", command], cwd=service_path)
        else:
            print("Usage: python run.py odoo [test|setup|update]")
    elif service == "gmail":
        if command:
            subprocess.run([sys.executable, "run.py", command], cwd=service_path)
        else:
            print("Usage: python run.py gmail [agent|debug|refresh]")
    elif service == "testing":
        if command:
            subprocess.run([sys.executable, "run.py", command], cwd=service_path)
        else:
            print("Usage: python run.py testing [core|invoice|approval|simple]")
    elif service == "config":
        config_dir = Path(__file__).parent / "config"
        if command == "setup":
            print("Running configuration setup...")
            print("Please edit: scripts/config/.env")
        elif command == "test":
            print("Configuration files in scripts/config/:")
            for file in config_dir.glob(".env*"):
                print(f"  - {file.name}")
        else:
            print("Config commands: setup, test")

if __name__ == "__main__":
    main()