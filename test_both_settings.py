import os
from pathlib import Path
from src.config.settings import settings as src_settings
from ai_employee.core.config import get_config

print(f"SRC PENDING_APPROVAL_PATH: {src_settings.PENDING_APPROVAL_PATH}")
config = get_config()
print(f"AI_EMPLOYEE PENDING_APPROVAL_PATH: {config.paths.pending_approval_path}")
