"""
Utility to load the company handbook markdown file.

Provides a single function ``load_handbook`` that reads the file pointed to by
``settings.COMPANY_HANDBOOK_PATH`` and returns its contents as a UTF‑8 string.

If the file does not exist or cannot be read, a ``FileProcessingException``
is raised so callers can handle the error appropriately.
"""

from pathlib import Path

from ..config.settings import COMPANY_HANDBOOK_PATH
from ..exceptions import FileProcessingException


def load_handbook() -> str:
    """Read and return the company handbook.

    Returns
    -------
    str
        The full markdown content of the handbook.

    Raises
    ------
    FileProcessingException
        If the handbook file is missing or cannot be read.
    """

    path = Path(COMPANY_HANDBOOK_PATH)
    if not path.is_file():
        raise FileProcessingException(f"Handbook file not found at {COMPANY_HANDBOOK_PATH}")
    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        raise FileProcessingException(f"Error reading handbook: {e}")
