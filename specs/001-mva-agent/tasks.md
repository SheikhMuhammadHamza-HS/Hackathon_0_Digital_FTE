# Tasks: Minimum Viable Agent (Digital FTE)

## Overview

Implementation of a Minimum Viable Agent with Perception-Reasoning-Memory loop that monitors an `/Inbox` folder for new files, creates trigger files in `/Needs_Action`, processes them with Claude Code, and updates a real-time `Dashboard.md`. This document outlines all tasks needed to complete the implementation.

## Phase 1: Setup

**Goal**: Initialize project structure and dependencies

- [X] T001 Create project root directory structure
- [X] T002 Create src/ directory and subdirectories (agents, watchers, models, services, cli, config, utils)
- [X] T003 Create tests/ directory and subdirectories (unit, integration, contract)
- [X] T004 Create requirements.txt with watchdog, python-dotenv, requests, pytest
- [X] T005 Create .env.example file with required environment variables
- [X] T006 Create __init__.py files in all Python directories
- [X] T007 Create initial README.md with project overview

## Phase 2: Foundational

**Goal**: Implement core configuration and utility components that are prerequisites for user stories

- [X] T008 [P] Create config/settings.py to load environment variables
- [X] T009 [P] Create utils/file_utils.py with file validation functions
- [X] T010 [P] Create models/file_metadata.py with FileMetadata class
- [X] T011 [P] Create models/dashboard.py with DashboardEntry class
- [X] T012 [P] Create models/trigger_file.py with TriggerFile class
- [X] T013 [P] Create models/agent_state.py with AgentState class
- [X] T014 Create logging setup in config module
- [X] T015 Create base exception classes

## Phase 3: User Story 1 - Folder Structure Setup (Priority: P1)

**Goal**: User runs setup script to initialize agent environment, creating required folder structure and configuration files

**Independent Test**: Can be fully tested by running the setup script and verifying that all required folders (`/Inbox`, `/Needs_Action`, `/Done`, `/Logs`) and files (`Dashboard.md`, `Company_Handbook.md`) are created

- [X] T016 [P] [US1] Create services/file_mover.py with move_file function
- [X] T017 [P] [US1] Create services/trigger_generator.py with create_trigger_file function
- [X] T018 [P] [US1] Create CLI setup command in src/cli/main.py
- [X] T019 [US1] Implement folder creation logic in CLI setup command
- [X] T020 [US1] Implement Dashboard.md creation with initial template
- [X] T021 [US1] Implement Company_Handbook.md creation with default content
- [X] T022 [US1] Create unit tests for setup functionality
- [X] T023 [US1] Test that all required folders are created successfully
- [X] T024 [US1] Test that initial configuration files are created with proper templates

## Phase 4: User Story 2 - Agent File Monitoring and Processing (Priority: P1)

**Goal**: Human user drops file into `/Inbox` folder, and agent automatically detects file, creates trigger in `/Needs_Action`, processes with Claude Code, updates dashboard, moves original file to `/Done`

**Independent Test**: Can be fully tested by dropping file in `/Inbox` and verifying it appears in dashboard with "Done" status while original file is moved to `/Done`

- [X] T025 [P] [US2] Create watchers/filesystem_watcher.py with event handler
- [X] T026 [P] [US2] Implement file detection and validation in watcher
- [X] T027 [P] [US2] Create agents/file_processor.py with Claude Code integration
- [X] T028 [US2] Integrate file validation with 10MB size limit check
- [X] T029 [US2] Implement trigger file creation with timestamp naming convention
- [X] T030 [US2] Implement file movement from `/Inbox` to `/Done`
- [X] T031 [US2] Connect filesystem watcher to trigger generation
- [X] T032 [US2] Implement Claude Code processing of trigger files
- [X] T033 [US2] Add error handling with exponential backoff retry mechanism
- [X] T034 [US2] Implement file type validation (PDF, DOCX, TXT, XLSX, PPTX, JPG, PNG, GIF)
- [X] T035 [US2] Create unit tests for file monitoring functionality
- [X] T036 [US2] Create integration tests for end-to-end file processing
- [X] T037 [US2] Test file detection within 5-second latency requirement
- [X] T038 [US2] Test that files are processed according to acceptance scenarios

## Phase 5: User Story 3 - Real-time Dashboard Updates (Priority: P2)

**Goal**: User monitors agent progress by viewing `Dashboard.md` file showing real-time status of processed files with timestamps and completion status

**Independent Test**: Can be fully tested by checking dashboard after file processing and verifying accurate status updates

- [X] T039 [P] [US3] Enhance dashboard model to manage entries collection
- [X] T040 [P] [US3] Implement real-time dashboard update functionality
- [X] T041 [US3] Create markdown table formatting for dashboard
- [X] T042 [US3] Connect file processing completion to dashboard updates
- [X] T043 [US3] Implement dashboard sorting by chronological order
- [X] T044 [US3] Add file type and duration tracking to dashboard entries
- [X] T045 [US3] Implement security logging for processed files
- [X] T046 [US3] Create unit tests for dashboard functionality
- [X] T047 [US3] Test that dashboard accurately reflects processed files with correct timestamps
- [X] T048 [US3] Test real-time updates when files are processed

## Phase 6: CLI Interface and Agent Control

**Goal**: Provide CLI commands to start, stop, and monitor the agent

- [X] T049 [P] Implement start command in CLI to initiate filesystem watching
- [X] T050 [P] Implement stop command in CLI to gracefully halt agent
- [X] T051 Implement status command showing current agent state
- [X] T052 Implement process-trigger command for manual trigger processing
- [X] T053 Add graceful shutdown handling for file watcher
- [X] T054 Create unit tests for CLI commands
- [X] T055 Test agent startup and shutdown functionality

## Phase 7: Security and Error Handling

**Goal**: Implement security measures and comprehensive error handling

- [X] T056 [P] Add encryption-at-rest for sensitive file processing
- [X] T057 [P] Implement access logging for file processing events
- [X] T058 Enhance error queue functionality for failed processing attempts
- [X] T059 Add permission error handling for filesystem operations
- [X] T060 Handle invalid file formats and corrupted files
- [X] T061 Implement retry mechanism with maximum 3 attempts
- [X] T062 Add logging for troubleshooting and observability
- [X] T063 Create unit tests for error handling scenarios

## Phase 8: Polish & Cross-Cutting Concerns

**Goal**: Complete the implementation with production-ready features

- [X] T064 [P] Add comprehensive logging throughout the application
- [X] T065 [P] Implement performance monitoring for 5-second detection requirement
- [X] T066 Add command-line argument parsing for configuration
- [X] T067 Create detailed README.md with usage instructions
- [X] T068 Add integration tests covering all user stories
- [X] T069 Run full test suite and fix any issues
- [X] T070 Document all modules with docstrings
- [X] T071 Final end-to-end testing of all functionality
- [X] T072 Prepare final implementation for delivery

## Dependencies

### User Story Order
1. **US2 (Agent File Monitoring)** depends on: US1 (Folder Structure Setup)
2. **US3 (Dashboard Updates)** depends on: US2 (Agent File Monitoring)
3. **US1 (Folder Structure Setup)** has no dependencies

### Parallel Execution Opportunities
- Tasks T008-T013 can run in parallel (foundational models and utilities)
- Tasks T016-T018 can run in parallel (core services)
- Tasks T025-T027 can run in parallel (watcher and processor)

## Implementation Strategy

**MVP Scope**: Just User Story 1 (Folder Structure Setup) and User Story 2 (Core File Processing) to deliver functional agent that can monitor, process, and move files.

**Incremental Delivery**:
- Sprint 1: Phase 1 (Setup) + Phase 2 (Foundational)
- Sprint 2: Phase 3 (Folder Setup) + Phase 4 (Core Processing) - MVP Deliverable
- Sprint 3: Phase 5 (Dashboard) + Phase 6 (CLI) - Full Functionality
- Sprint 4: Phase 7 (Security/Error Handling) + Phase 8 (Polish) - Production Ready