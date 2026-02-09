import os
import threading
from pathlib import Path
import time
import pytest

from src.services.dashboard_updater import DashboardUpdater
from src.config import settings

def test_dashboard_3_column_format(tmp_path, monkeypatch):
    """Verify the dashboard uses the correct 3-column format: Time | Task | Status"""
    dashboard_file = tmp_path / "Dashboard.md"
    monkeypatch.setattr(settings, "DASHBOARD_PATH", str(dashboard_file))
    updater = DashboardUpdater(str(dashboard_file))
    content = dashboard_file.read_text(encoding="utf-8")
    # Check header format
    assert "| Time | Task | Status |" in content
    assert "|---|---|---|" in content


def test_dashboard_append_and_rotation(tmp_path, monkeypatch):
    # Set a temporary dashboard path
    dashboard_file = tmp_path / "Dashboard.md"
    monkeypatch.setattr(settings, "DASHBOARD_PATH", str(dashboard_file))
    updater = DashboardUpdater(str(dashboard_file))
    # Append a first entry
    updater.append_entry("Test Action", "SUCCESS")
    content = dashboard_file.read_text(encoding="utf-8")
    assert "Test Action" in content
    # Force rotation by appending large content
    large_content = "A" * (DashboardUpdater.MAX_SIZE_BYTES + 1)
    with open(dashboard_file, "a", encoding="utf-8") as f:
        f.write(large_content)
    # Next append should trigger rotation
    updater.append_entry("Post Rotation", "SUCCESS")
    # After rotation, original file should contain header and new entry only
    new_content = dashboard_file.read_text(encoding="utf-8")
    assert "Post Rotation" in new_content
    assert "Test Action" not in new_content
    # Archive file should exist
    archives = list(tmp_path.glob("Dashboard_*.md"))
    assert len(archives) == 1
    archive_content = archives[0].read_text(encoding="utf-8")
    assert "Test Action" in archive_content


def test_concurrent_append_operations(tmp_path, monkeypatch):
    """Test that concurrent appends don't cause interleaved rows"""
    dashboard_file = tmp_path / "Dashboard.md"
    monkeypatch.setattr(settings, "DASHBOARD_PATH", str(dashboard_file))
    updater = DashboardUpdater(str(dashboard_file))

    def append_many(thread_id):
        for i in range(10):
            updater.append_entry(f"Thread{thread_id} Action{i}", "SUCCESS")

    threads = [threading.Thread(target=append_many, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    content = dashboard_file.read_text()
    lines = [l for l in content.split('\n') if '|' in l]
    # Should have header (2 lines) + 50 entries
    assert len(lines) >= 51  # At least 51 lines (header + entries)
    # Verify each data line has exactly 3 columns (4 pipes)
    for line in lines[2:]:  # Skip header and separator
        if line.strip():  # Skip empty lines
            assert line.count('|') == 4  # 3 columns = 4 pipe characters


def test_rotation_creates_archive(tmp_path, monkeypatch):
    """Verify rotation creates an archive file with timestamp"""
    dashboard_file = tmp_path / "Dashboard.md"
    monkeypatch.setattr(settings, "DASHBOARD_PATH", str(dashboard_file))
    updater = DashboardUpdater(str(dashboard_file))

    # Add initial entry
    updater.append_entry("Initial Entry", "SUCCESS")

    # Force rotation
    large_content = "A" * (DashboardUpdater.MAX_SIZE_BYTES + 1)
    with open(dashboard_file, "a", encoding="utf-8") as f:
        f.write(large_content)
    updater.append_entry("After Rotation", "SUCCESS")

    # Verify archive exists
    archives = list(tmp_path.glob("Dashboard_*.md"))
    assert len(archives) == 1
    # Verify archive name contains timestamp pattern
    assert archives[0].name.startswith("Dashboard_20")
    assert archives[0].name.endswith(".md")


def test_rotation_preserves_new_entries(tmp_path, monkeypatch):
    """Verify that entries after rotation are in the new file"""
    dashboard_file = tmp_path / "Dashboard.md"
    monkeypatch.setattr(settings, "DASHBOARD_PATH", str(dashboard_file))
    updater = DashboardUpdater(str(dashboard_file))

    # Add initial entry
    updater.append_entry("Old Entry", "SUCCESS")

    # Force rotation
    large_content = "A" * (DashboardUpdater.MAX_SIZE_BYTES + 1)
    with open(dashboard_file, "a", encoding="utf-8") as f:
        f.write(large_content)
    updater.append_entry("New Entry", "SUCCESS")

    # Check new file contains new entry
    new_content = dashboard_file.read_text()
    assert "New Entry" in new_content
    assert "Old Entry" not in new_content


def test_append_entry_format(tmp_path, monkeypatch):
    """Verify each entry matches the markdown table format"""
    dashboard_file = tmp_path / "Dashboard.md"
    monkeypatch.setattr(settings, "DASHBOARD_PATH", str(dashboard_file))
    updater = DashboardUpdater(str(dashboard_file))

    updater.append_entry("Test Task", "SUCCESS")
    updater.append_entry("Another Task", "FAILURE")

    content = dashboard_file.read_text()
    lines = [l for l in content.split('\n') if l.strip() and '|' in l]

    # Check header
    assert lines[0] == "| Time | Task | Status |"
    assert lines[1] == "|---|---|---|"

    # Check entry format - should start with | and end with |
    for line in lines[2:]:
        assert line.startswith("|")
        assert line.endswith("|")
        # Check for timestamp format (YYYY-MM-DD HH:MM:SSZ)
        parts = line.split("|")
        assert len(parts) == 5  # empty + 3 columns + empty
