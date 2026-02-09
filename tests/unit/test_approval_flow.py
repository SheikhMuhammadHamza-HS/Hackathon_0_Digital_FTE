import threading
import time
from pathlib import Path

import pytest

from src.watchers.approval_watcher import ApprovalWatcher
from src.services.action_executor import ActionExecutor
from src.services.email_sender import EmailSender
from src.services.linkedin_poster import LinkedInPoster
from src.services.dashboard_updater import DashboardUpdater
from src.services.file_mover import FileMover
from src.config import settings


# Helper to monkeypatch settings paths for isolated test environment
def _setup_temp_dirs(tmp_path):
    base = tmp_path / "project"
    base.mkdir()
    # Create required folders
    approved = base / "Approved"
    approved.mkdir()
    done = base / "Done"
    done.mkdir()
    failed = base / "Failed"
    failed.mkdir()
    # Override settings paths
    settings.APPROVED_PATH = str(approved)
    settings.DONE_PATH = str(done)
    settings.FAILED_PATH = str(failed)
    return approved, done, failed

class MockEmailSender(EmailSender):
    def __init__(self, succeed=True):
        self.succeed = succeed
        self.called = False
    def send_draft(self, draft_path: Path) -> bool:
        self.called = True
        return self.succeed

class MockLinkedInPoster(LinkedInPoster):
    def __init__(self, succeed=True):
        self.succeed = succeed
        self.called = False
    def post_draft(self, draft_path: Path) -> bool:
        self.called = True
        return self.succeed

def test_approval_watcher_email_success(tmp_path, monkeypatch):
    approved, done, failed = _setup_temp_dirs(tmp_path)
    # Prepare a simple draft with Platform header
    draft = approved / "email_draft.md"
    draft.write_text("Platform: email\nSubject: Test\n\nBody", encoding="utf-8")
    # Patch ActionExecutor to use mock sender
    mock_email = MockEmailSender(succeed=True)
    mock_linkedin = MockLinkedInPoster()
    monkeypatch.setattr(ActionExecutor, "__init__", lambda self: setattr(self, "email_sender", mock_email) or setattr(self, "linkedin_poster", mock_linkedin))
    # Patch is_safe_path to always return True for tests
    monkeypatch.setattr("src.watchers.approval_watcher.is_safe_path", lambda p, b: True)
    
    # Run watcher in a thread with stop event
    stop_event = threading.Event()
    watcher = ApprovalWatcher(poll_interval=0.1, stop_event=stop_event)
    t = threading.Thread(target=watcher.start, daemon=True)
    t.start()
    # Allow some time for processing
    time.sleep(0.3)
    stop_event.set()
    t.join()
    # Verify file moved to Done and mock called
    assert (done / "email_draft.md").exists()
    assert not (approved / "email_draft.md").exists()
    assert mock_email.called
    assert not mock_linkedin.called
    # Ensure no file in Failed
    assert not (failed / "email_draft.md").exists()

def test_approval_watcher_linkedin_failure(tmp_path, monkeypatch):
    approved, done, failed = _setup_temp_dirs(tmp_path)
    draft = approved / "linkedin_draft.md"
    draft.write_text("Platform: linkedin\nSubject: Test\n\nBody", encoding="utf-8")
    mock_email = MockEmailSender()
    mock_linkedin = MockLinkedInPoster(succeed=False)
    monkeypatch.setattr(ActionExecutor, "__init__", lambda self: setattr(self, "email_sender", mock_email) or setattr(self, "linkedin_poster", mock_linkedin))
    
    # Patch is_safe_path to always return True for tests
    monkeypatch.setattr("src.watchers.approval_watcher.is_safe_path", lambda p, b: True)

    stop_event = threading.Event()
    watcher = ApprovalWatcher(poll_interval=0.1, stop_event=stop_event)
    t = threading.Thread(target=watcher.start, daemon=True)
    t.start()
    time.sleep(0.3)
    stop_event.set()
    t.join()
    # Verify moved to Failed and mock called
    assert (failed / "linkedin_draft.md").exists()
    assert not (approved / "linkedin_draft.md").exists()
    assert not (done / "linkedin_draft.md").exists()
    assert mock_linkedin.called
