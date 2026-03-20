import os
from pathlib import Path
from ai_employee.core.config import get_config
from dotenv import load_dotenv

load_dotenv()
config = get_config()
print(f"PENDING_APPROVAL_PATH: {config.paths.pending_approval_path}")
print(f"NEEDS_ACTION_PATH: {config.paths.needs_action_path}")
print(f"exists: {config.paths.pending_approval_path.exists()}")
if config.paths.pending_approval_path.exists():
    print(f"files: {list(config.paths.pending_approval_path.glob('*.md'))}")
