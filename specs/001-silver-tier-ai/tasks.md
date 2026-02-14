# Tasks: Personal AI Employee (Silver Tier)

**Input**: Design documents from `/specs/001-silver-tier-ai/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

## Phase 1: Setup (Shared Infrastructure)

- [X] T001 Create project structure per implementation plan (`./` root with `src/`, `tests/`, `configs/` directories)
- [X] T002 Initialize Python 3.10 project with `poetry init` and add dependencies (`watchdog`, `python-dotenv`, `google-generativeai`, `requests`, `pytest`)
- [X] T003 [P] Configure linting (ruff) and formatting (black) tools (`pyproject.toml`)
- [X] T004 Add environment file template `.env.example` and .gitignore entries for `.env` and `__pycache__/`
- [X] T005 [P] Set up basic logging configuration (`src/config/logging_config.py`)

## Phase 2: Foundational (Blocking Prerequisites)

- [X] T006 Setup audit logging to `/Vault/Logs/YYYY-MM-DD.json` (`src/services/logging_service.py`)
- [X] T007 [P] Implement file path validation utilities to prevent directory traversal (`src/utils/security.py`)
- [X] T008 Create base `AgentState` model with status tracking (`src/models/agent_state.py`)
- [X] T009 Configure error handling middleware for graceful failures (`src/services/error_handler.py`)
- [X] T010 Setup configuration loader using `python-dotenv` (`src/config/settings.py`)

---

## Phase 3: User Story 1 - Multi-Input Task Monitoring (Priority: P1) 🎯 MVP

**Goal**: Continuously monitor Gmail inbox and local `/Inbox` folder, create task files in `/Needs_Action`.

**Independent Test**: Inject a test file into `/Inbox` and a mock Gmail unread email; verify corresponding task files appear in `/Needs_Action` within 2 minutes.

- [X] T011 [US1] Implement Gmail watcher using Google API (`src/watchers/gmail_watcher.py`)
- [X] T012 [US1] Implement filesystem watcher for `/Inbox` using watchdog (`src/watchers/filesystem_watcher.py`)
- [X] T013 [US1] Create task file generation logic with content‑based hashing (`src/services/task_generator.py`)
- [X] T014 [US1] Add duplicate detection using hash comparison (`src/services/task_generator.py`)
- [X] T015 [US1] Write unit tests for task generation and duplicate handling (`tests/unit/test_task_generator.py`)

## Phase 4: User Story 2 - Automated Email Reply Drafting (Priority: P2)

**Goal**: Read email tasks, consult `Company_Handbook.md`, draft reply, save to `/Pending_Approval`.

**Independent Test**: Provide a sample email task file; verify a draft file is created with correct metadata and includes original email content.

- [x] T016 [US2] Parse email task files and extract content (`src/agents/email_processor.py`)
- [x] T017 [US2] Load reply guidelines from `Company_Handbook.md` (`src/utils/handbook_loader.py`)
- [x] T018 [US2] Generate email draft with `Subject:` and `To:` headers in body using Gemini API (`src/agents/email_processor.py`)
- [x] T019 [US2] Save draft to `/Pending_Approval` folder (`src/services/draft_store.py`)
- [x] T020 [US2] Write unit tests under `tests/unit/` and mock external APIs if keys missing (`tests/unit/test_email_processor.py`)

## Phase 5: User Story 3 - Social Media Content Creation (Priority: P3)

**Goal**: On schedule (every Monday 9:00 AM), read `Business_Goals.md` and create LinkedIn post draft in `/Pending_Approval`.

**Independent Test**: Trigger scheduled run; verify a LinkedIn draft file appears with recent business updates.

- [x] T021 [US3] Implement scheduler for weekly execution (`src/services/scheduler.py`)
- [x] T022 [US3] Read `Business_Goals.md` and extract latest metrics (`src/utils/goals_reader.py`)
- [x] T023 [US3] Generate LinkedIn post draft via Gemini API (`src/agents/linkedin_processor.py`)
- [x] T024 [US3] Save draft to `/Pending_Approval` with appropriate metadata (`src/services/draft_store.py`)
- [ ] T025 [US3] Write unit tests for scheduler and draft creation (`tests/unit/test_linkedin_processor.py`)

## Phase 6: User Story 4 - Human-in-the-Loop Approval Execution (Priority: P1)

**Goal**: Detect moves from `/Pending_Approval` to `/Approved`, parse metadata, execute action (send email or post), move file to `/Done`.

**Independent Test**: Move a prepared draft to `/Approved`; verify the external action is performed and the file ends up in `/Done`.

- [x] T026 [US4] Watch `/Approved` folder for new files (`src/watchers/approval_watcher.py`)
- [x] T027 [US4] Parse action metadata and route to appropriate executor (`src/services/action_executor.py`)
- [x] T028 [US4] Implement email sending using Gmail API (`src/agents/email_sender.py`)
- [x] T029 [US4] Implement LinkedIn posting via API (`src/agents/linkedin_poster.py`)
- [x] T030 [US4] Move processed files to `/Done` and log outcome (`src/services/file_mover.py`)
- [x] T031 [US4] Add retry logic with exponential backoff for failures (`src/services/retry_handler.py`)
- [x] T032 [US4] Write integration tests for approval flow (`tests/integration/test_approval_flow.py`)

## Phase 7: User Story 5 - Real-Time Dashboard Updates (Priority: P2)

**Goal**: Update `Dashboard.md` with system status, pending tasks, drafts awaiting approval, recent activity, and simulated bank balance.

**Independent Test**: Simulate events (new task, draft creation, action execution) and verify `Dashboard.md` reflects changes within 10 seconds.

- [x] T033 [US5] Design dashboard markdown template using 3-column table: Time | Task | Status (`Dashboard.md`)
- [x] T034 [US5] Implement dashboard updater that maintains chronological order (`src/services/dashboard_updater.py`)
- [x] T035 [US5] Hook updater into event emitters and add CLI command `status` update logic (`src/cli/main.py`)
- [x] T036 [US5] Add unit tests for dashboard content generation (`tests/unit/test_dashboard_updater.py`)

## Phase 8: Polish & Cross‑Cutting Concerns

- [x] T037 [P] Add comprehensive documentation in `docs/` for setup, usage, and architecture
- [x] T038 Code cleanup and refactoring for readability
- [x] T039 Performance optimization of watcher loops (reduce CPU usage)
- [x] T040 [P] Additional unit tests for edge cases (file size limit, corrupt files) (`tests/unit/`)
- [x] T041 Security hardening: ensure secret handling never writes to logs
- [X] T043 [P] Record AI exchange as PHR
- [x] T042 Run quickstart validation script to verify end‑to‑end workflow

---

## Dependencies & Execution Order

- **Setup (Phase 1)** must complete before **Foundational (Phase 2)**.
- **Foundational (Phase 2)** blocks all user story phases.
- After **Foundational**, user stories **US1‑US5** can proceed in parallel (if team capacity allows).
- **Polish (Phase 8)** depends on completion of desired user stories.

## Parallel Opportunities

- All tasks marked `[P]` can be executed concurrently across different files.
- Setup tasks `[P]` (T003, T005) run in parallel.
- Foundational tasks `[P]` (T007, T008) run in parallel.
- User story tasks within the same story (e.g., T011‑T015) can be parallelized where no explicit dependencies exist.
- Different user stories can be worked on simultaneously by separate developers.
- [X] T043 Update task file after recent changes (settings, file_processor, dashboard)
- [X] T044 Finalize Silver Tier base implementation fixes and verify all tests pass
- [X] T045 Integrated Gmail Automation <!-- id: 37 -->
    - [X] Complete GmailWatcher credentials logic
    - [X] Update Gmail polling for .eml metadata
    - [X] Integrate Gmail triggers into FileWatcher/Orchestrator
- [ ] T046 Integrated LinkedIn Automation Enhancements <!-- id: 38 -->
    - [ ] Refine LinkedIn post drafting prompts
    - [ ] Improve scheduler robustness
- [X] T047 [US1] Implement WhatsApp watcher using Playwright browser automation (`src/watchers/whatsapp_watcher.py`)
- [X] T048 [US2/US3] Implement `Plan.md` generation before drafting for complex reasoning tracking (`src/services/planner.py`)
- [X] T049 [US4] Transition internal executors to official MCP Server architecture (email-mcp, browser-mcp)
- [X] T050 [US1-US4] Implement "Ralph Wiggum" loop (automated persistence) to ensure autonomous task completion until `Needs_Action` is empty
- [X] T051 [US5] Implement "Monday Morning CEO Briefing" routine as per hackathon requirements
