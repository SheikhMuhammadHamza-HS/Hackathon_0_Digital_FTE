# Feature Specification: Minimum Viable Agent (Digital FTE)

**Feature Branch**: `001-mva-agent`
**Created**: 2026-02-06
**Status**: Draft
**Input**: User description: "Build a Minimum Viable Agent (Digital FTE) with Perception-Reasoning-Memory loop"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Agent File Monitoring and Processing (Priority: P1)

A human user drops a file into the `/Inbox` folder, and the agent automatically detects the new file, creates a trigger in `/Needs_Action`, processes the file by updating the dashboard, and moves the original file to `/Done`.

**Why this priority**: This is the core functionality that demonstrates the Perception → Reasoning → Memory loop and provides immediate value to users by automating file processing.

**Independent Test**: Can be fully tested by dropping a file in `/Inbox` and verifying that it appears in the dashboard with "Done" status, while the original file is moved to `/Done`. Delivers automated file processing capability.

**Acceptance Scenarios**:

1. **Given** user has placed a file in `/Inbox`, **When** the filesystem watcher detects the file, **Then** a corresponding trigger file is created in `/Needs_Action`
2. **Given** a trigger file exists in `/Needs_Action`, **When** Claude Code processes the trigger, **Then** the dashboard is updated and the original file is moved to `/Done`

---

### User Story 2 - Folder Structure Setup (Priority: P1)

A user runs a setup script to initialize the agent environment, which creates the required folder structure and configuration files.

**Why this priority**: This is foundational infrastructure that must exist before the agent can function properly.

**Independent Test**: Can be fully tested by running the setup script and verifying that all required folders (`/Inbox`, `/Needs_Action`, `/Done`, `/Logs`) and files (`Dashboard.md`, `Company_Handbook.md`) are created. Delivers a properly configured environment.

**Acceptance Scenarios**:

1. **Given** a clean environment, **When** the setup script is executed, **Then** all required folders are created successfully
2. **Given** the setup script, **When** it runs, **Then** the initial configuration files are created with proper templates

---

### User Story 3 - Real-time Dashboard Updates (Priority: P2)

A user monitors the agent's progress by viewing the `Dashboard.md` file, which shows real-time status of processed files with timestamps and completion status.

**Why this priority**: Provides visibility into agent operations, allowing users to track progress and verify successful processing.

**Independent Test**: Can be fully tested by checking the dashboard after file processing and verifying accurate status updates. Delivers transparency into agent operations.

**Acceptance Scenarios**:

1. **Given** a file has been processed by the agent, **When** user views `Dashboard.md`, **Then** the file appears in the dashboard table with correct timestamp and status
2. **Given** multiple files have been processed, **When** dashboard is viewed, **Then** all files appear in chronological order with accurate status

---

### Edge Cases

- What happens when the inbox folder is missing or inaccessible?
- How does the system handle invalid file formats or corrupted files?
- What occurs when the file system watcher encounters permission errors?
- How does the agent handle multiple simultaneous file drops?
- What happens when Claude Code API is unavailable during processing?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST create `/Inbox`, `/Needs_Action`, `/Done`, and `/Logs` folders when initialized
- **FR-002**: System MUST monitor `/Inbox` folder for new files with 5-second detection latency
- **FR-003**: System MUST generate trigger files in `/Needs_Action` with timestamp-based naming convention
- **FR-004**: System MUST process trigger files by updating `Dashboard.md` with file status information
- **FR-005**: System MUST move processed files from `/Inbox` to `/Done` folder upon completion
- **FR-006**: System MUST load API keys from `.env` file for Claude Code integration
- **FR-007**: System MUST maintain a live-updating dashboard showing current task status
- **FR-008**: System MUST generate metadata triggers with file type, source path, and timestamp
- **FR-009**: System MUST follow the Perception → Reasoning → Memory operational loop
- **FR-010**: System MUST prevent permanent deletion of files (only moves, never deletes)

### Key Entities

- **Trigger File**: Represents a detected file event with metadata (type, source path, timestamp, status) that initiates processing
- **Dashboard Entry**: A record in the dashboard table representing processed files with time, task name, and completion status
- **File Metadata**: Information about processed files including original path, timestamp, and processing outcome
- **Agent State**: Current operational state of the agent indicating which files are pending, in progress, or completed

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: File detection occurs within 5 seconds of placement in `/Inbox` folder
- **SC-002**: 100% of files dropped in `/Inbox` are successfully processed and moved to `/Done` folder
- **SC-003**: Dashboard accurately reflects all processed files with correct timestamps and status indicators
- **SC-004**: System maintains the Perception → Reasoning → Memory loop operation continuously without interruption
- **SC-005**: Setup process completes in under 30 seconds with all required folders and files created

## Clarifications

### Session 2026-02-06

- Q: How should the system handle potentially sensitive files and what security measures are required? → A: All files are treated with standard security protocols, with encryption at rest and access logging

- Q: Are there any file size limits that should be enforced for processed files? → A: Maximum 10MB per file to balance functionality with resource constraints

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST create `/Inbox`, `/Needs_Action`, `/Done`, and `/Logs` folders when initialized
- **FR-002**: System MUST monitor `/Inbox` folder for new files with 5-second detection latency
- **FR-003**: System MUST generate trigger files in `/Needs_Action` with timestamp-based naming convention
- **FR-004**: System MUST process trigger files by updating `Dashboard.md` with file status information
- **FR-005**: System MUST move processed files from `/Inbox` to `/Done` folder upon completion
- **FR-006**: System MUST load API keys from `.env` file for Claude Code integration
- **FR-007**: System MUST maintain a live-updating dashboard showing current task status
- **FR-008**: System MUST generate metadata triggers with file type, source path, and timestamp
- **FR-009**: System MUST follow the Perception → Reasoning → Memory operational loop
- **FR-010**: System MUST prevent permanent deletion of files (only moves, never deletes)
- **FR-011**: System MUST implement standard security protocols including encryption at rest and access logging for all processed files
- **FR-012**: System MUST update the dashboard in real-time as files are processed (immediately when status changes)
- **FR-013**: System MUST enforce a maximum file size limit of 10MB per file to balance functionality with resource constraints

### Key Entities

- **Trigger File**: Represents a detected file event with metadata (type, source path, timestamp, status) that initiates processing
- **Dashboard Entry**: A record in the dashboard table representing processed files with time, task name, and completion status
- **File Metadata**: Information about processed files including original path, timestamp, and processing outcome
- **Agent State**: Current operational state of the agent indicating which files are pending, in progress, or completed
