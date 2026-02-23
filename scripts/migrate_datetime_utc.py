#!/usr/bin/env python3
"""Script to replace datetime.now(timezone.utc) with datetime.now(datetime.UTC) in all Python files."""

import os
import re
from pathlib import Path
from typing import List, Tuple

def find_python_files(root_dir: Path) -> List[Path]:
    """Find all Python files in the directory tree."""
    python_files = []
    for file_path in root_dir.rglob("*.py"):
        # Skip certain directories
        if any(skip_dir in str(file_path) for skip_dir in [".git", "__pycache__", "node_modules", ".venv", "venv"]):
            continue
        python_files.append(file_path)
    return python_files

def migrate_datetime_in_file(file_path: Path) -> Tuple[int, int]:
    """Migrate datetime.now(timezone.utc) to datetime.now(datetime.UTC) in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Add timezone import if not present and datetime.now(timezone.utc) is found
        if 'datetime.now(timezone.utc)' in content and 'from datetime import' in content:
            # Check if timezone is already imported
            if 'timezone' not in content:
                # Add timezone to existing datetime imports
                content = re.sub(
                    r'from datetime import datetime',
                    'from datetime import datetime, timezone, timezone',
                    content
                )
            elif 'from datetime import' in content and 'datetime' in content:
                # Add timezone to import if not already there
                content = re.sub(
                    r'(from datetime import [^)]*datetime)',
                    r'\1, timezone',
                    content
                )

        # Replace datetime.now(timezone.utc) with datetime.now(timezone.utc)
        content = content.replace('datetime.now(timezone.utc)', 'datetime.now(timezone.utc)')

        # Write back if changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return 1, 0
        else:
            return 0, 0

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return 0, 1

def main():
    """Main migration function."""
    root_dir = Path(__file__).parent.parent
    print(f"Searching for Python files in: {root_dir}")

    python_files = find_python_files(root_dir)
    print(f"Found {len(python_files)} Python files")

    total_migrated = 0
    total_errors = 0

    for file_path in python_files:
        migrated, errors = migrate_datetime_in_file(file_path)
        total_migrated += migrated
        total_errors += errors

        if migrated:
            print(f"[MIGRATED] {file_path.relative_to(root_dir)}")
        elif errors:
            print(f"[ERROR] {file_path.relative_to(root_dir)}")

    print(f"\nMigration complete:")
    print(f"  Files migrated: {total_migrated}")
    print(f"  Errors: {total_errors}")
    print(f"  Total files: {len(python_files)}")

if __name__ == "__main__":
    main()