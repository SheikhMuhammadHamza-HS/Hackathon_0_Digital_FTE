# Implementation Plan: Minimum Viable Agent (Digital FTE)

**Branch**: `001-mva-agent` | **Date**: 2026-02-06 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-mva-agent/spec.md`

**Note**: This template is filled in by the `/sp.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implementation of a Minimum Viable Agent with Perception-Reasoning-Memory loop that monitors an `/Inbox` folder for new files, creates trigger files in `/Needs_Action`, processes them with Claude Code, and updates a real-time `Dashboard.md`. The agent will use Python 3.10+ with the watchdog library for cross-platform file monitoring and implement robust error handling with exponential backoff.

## Technical Context

**Language/Version**: Python 3.10+ (as specified in feature requirements)
**Primary Dependencies**: watchdog (for file monitoring), python-dotenv (for env loading), os/pathlib (for file operations)
**Storage**: File-based storage using local filesystem (folders: /Inbox, /Needs_Action, /Done, /Logs)
**Testing**: pytest (for unit and integration tests)
**Target Platform**: Cross-platform (Windows, macOS, Linux)
**Project Type**: Single executable agent application
**Performance Goals**: File detection within 5 seconds (as specified in requirements)
**Constraints**: Maximum 10MB file size limit, Claude Code API integration, real-time dashboard updates
**Scale/Scope**: Single user/local-first architecture, designed for individual use

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Library-First**: N/A - This is an agent application rather than a library
**CLI Interface**: PASSED - Will expose functionality via CLI commands (setup, start, stop, status)
**Test-First**: PASSED - TDD approach will be used with tests written before implementation
**Integration Testing**: PASSED - Integration tests will cover filesystem monitoring, API integration, and dashboard updates
**Observability**: PASSED - Structured logging will be implemented for debugging and monitoring
**Non-Negotiables**: PASSED - All requirements can be met with test-first approach

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/sp.plan command output)
├── research.md          # Phase 0 output (/sp.plan command)
├── data-model.md        # Phase 1 output (/sp.plan command)
├── quickstart.md        # Phase 1 output (/sp.plan command)
├── contracts/           # Phase 1 output (/sp.plan command)
└── tasks.md             # Phase 2 output (/sp.tasks command - NOT created by /sp.plan)
```

### Source Code (repository root)

```text
src/
├── agents/
│   ├── __init__.py
│   └── file_processor.py      # Claude Code integration for processing triggers
├── watchers/
│   ├── __init__.py
│   └── filesystem_watcher.py  # Monitors /Inbox for new files
├── models/
│   ├── __init__.py
│   ├── file_metadata.py       # File metadata and trigger file handling
│   └── dashboard.py           # Dashboard update and management
├── services/
│   ├── __init__.py
│   ├── file_mover.py          # Handles moving files between folders
│   └── trigger_generator.py   # Creates trigger files in /Needs_Action
├── cli/
│   ├── __init__.py
│   └── main.py               # Main CLI entry point (setup, start, stop)
├── config/
│   ├── __init__.py
│   └── settings.py           # Configuration and environment loading
└── utils/
    ├── __init__.py
    └── file_utils.py         # File operations helper functions

tests/
├── unit/
│   ├── test_models/
│   ├── test_services/
│   └── test_watchers/
├── integration/
│   ├── test_filesystem_integration.py
│   └── test_dashboard_updates.py
└── contract/
    └── test_trigger_contracts.py

.env.example                           # Example environment file
filesystem_watcher.py                  # Main entry point script
README.md                              # Usage instructions
requirements.txt                       # Python dependencies
```

**Structure Decision**: Selected single project structure with modular organization separating concerns into distinct modules: agents for AI processing, watchers for filesystem monitoring, models for data handling, services for business logic, CLI for user interaction, and utilities for helper functions.

## Post-Design Constitution Check

*Re-evaluation after Phase 1 design*

**Library-First**: N/A - Confirmed as application rather than library
**CLI Interface**: PASSED - Confirmed with main CLI entry point in `src/cli/main.py`
**Test-First**: PASSED - Confirmed with comprehensive test structure (unit, integration, contract)
**Integration Testing**: PASSED - Confirmed with specific tests for filesystem monitoring and Claude Code integration
**Observability**: PASSED - Confirmed with structured logging planned in `/Logs` directory
**Non-Negotiables**: PASSED - All design decisions support test-first approach

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
