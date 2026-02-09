# Specification: Personal AI Employee (Silver Tier)
**Version:** 1.0
**Tier:** Silver (Functional Assistant)
**Architecture:** Local-First (Obsidian + Claude Code + MCP)

---

## 1. Constitution & Safety Laws (Must Follow)
*These rules are non-negotiable and override all other instructions.*

1.  **Local-First Data:** All user data, logs, and task states must reside in the local Obsidian Vault. No data leaves the machine unless explicitly required for an external action (e.g., sending an email).
2.  **Secret Management:** NEVER write API keys, passwords, or tokens into Markdown files. Always use a `.env` file listed in `.gitignore`.
3.  **Human-in-the-Loop (HITL):** The Agent cannot perform "Sensitive Actions" (sending emails, posting to LinkedIn, deleting files) without explicit human approval.
    *   *Mechanism:* Agent creates a file in `/Pending_Approval`. Action only executes when the Human moves it to `/Approved`.
4.  **Audit Trail:** Every action taken by the Agent (read, write, execute) must be logged in `/Vault/Logs/YYYY-MM-DD.json`.
5.  **Lazy Agent Prevention:** Use the "Ralph Wiggum" loop pattern (Stop Hook) to ensure tasks are fully completed before the Agent exits.

---

## 2. Project Scope (Silver Tier)
The goal is to build a "Functional Assistant" that operates 24/7 on a local machine. It connects "Perception" (Watchers) to "Action" (MCP) via "Reasoning" (Claude).

### Core Capabilities:
1.  **Multi-Input Perception:** Monitor Gmail and Local File System for new tasks.
2.  **Autonomous Social Media:** Draft and schedule LinkedIn posts about business updates.
3.  **Reasoning Engine:** Claude Code reads inputs and generates `Plan.md` files.
4.  **External Action:** Send emails via Gmail API using an MCP Server.
5.  **Scheduling:** Run specific tasks (e.g., Daily Briefing) via Cron or Task Scheduler.

---

## 3. Architecture & Data Flow

### A. The Vault Structure (Database)
The Obsidian Vault is the "State Machine". The folder structure implies status:
*   `/Inbox`: Raw inputs (PDFs, notes).
*   `/Needs_Action`: Trigger files created by Watchers (e.g., `EMAIL_123.md`).
*   `/Plans`: Claude's reasoning steps for complex tasks.
*   `/Pending_Approval`: Drafts waiting for human review.
*   `/Approved`: Files moved here trigger the "Action" layer.
*   `/Done`: Completed tasks (archive).
*   `/Logs`: JSON execution logs.
*   `Dashboard.md`: Real-time status center.
*   `Company_Handbook.md`: Rules and context for the AI.

### B. Perception Layer (The Watchers)
*Technology:* Python Scripts (run via PM2 or loop)
1.  **Gmail Watcher:** Polls Gmail API every 2 minutes. If a thread is "Unread" AND "Important", converts it to Markdown and saves to `/Needs_Action`.
2.  **FileSystem Watcher:** Monitors `/Inbox`. If a file is dropped, moves it to `/Needs_Action` with a metadata wrapper.

### C. Action Layer (The Hands)
*Technology:* Model Context Protocol (MCP)
1.  **Email MCP Server:** Node.js server exposing `send_email` tool.
2.  **LinkedIn Action:** (Simplified for Silver) A Python script triggered by the Orchestrator to post content found in `/Approved`.

---

## 4. Functional Requirements (EARS Syntax)

### Requirement 1: Dashboard Management
*   **Trigger:** System startup or Task Completion.
*   **System Shall:** Update `Dashboard.md` with:
    *   Current Bank Balance (simulated or read from CSV).
    *   Count of files in `/Needs_Action`.
    *   List of items in `/Pending_Approval`.

### Requirement 2: Email Processing Flow
*   **Trigger:** New file appears in `/Needs_Action` (created by Gmail Watcher).
*   **System Shall:**
    1.  Read the email content.
    2.  Check `Company_Handbook.md` for reply guidelines.
    3.  Draft a reply in `/Pending_Approval` (e.g., `REPLY_Client_A.md`).
    4.  NOT send the email immediately.

### Requirement 3: LinkedIn Promotion
*   **Trigger:** Scheduled task (Every Monday at 9:00 AM).
*   **System Shall:**
    1.  Read `Business_Goals.md` or recent project updates.
    2.  Draft a professional LinkedIn post about recent progress.
    3.  Save the draft to `/Pending_Approval/LINKEDIN_Draft_Date.md`.

### Requirement 4: HITL Execution
*   **Trigger:** User moves a file from `/Pending_Approval` to `/Approved`.
*   **System Shall:**
    1.  Detect the file movement.
    2.  Parse the file for Action Metadata (Type: Email/Post, To, Body).
    3.  Call the appropriate MCP Server/Script to execute.
    4.  Move file to `/Done` upon success.
    5.  Log result to `/Vault/Logs`.

---

## 5. Implementation Task List (Step-by-Step)

### Phase 1: Foundation Setup
- [ ] **Task 1.1:** Initialize Obsidian Vault with required folders (`Inbox`, `Needs_Action`, `Pending_Approval`, `Approved`, `Done`, `Logs`).
- [ ] **Task 1.2:** Create `Company_Handbook.md` with basic persona rules.
- [ ] **Task 1.3:** Set up Python environment (`uv` or `venv`) and install `watchdog`, `google-api-python-client`, `schedule`.
- [ ] **Task 1.4:** Create `.env` file template (add to `.gitignore`).

### Phase 2: The Eyes (Watchers)
- [ ] **Task 2.1:** Create `src/watchers/gmail_watcher.py` to poll Gmail and write Markdown files.
- [ ] **Task 2.2:** Create `src/watchers/file_watcher.py` to monitor local drops.
- [ ] **Task 2.3:** Create a `start_watchers.py` script to run both processes simultaneously (or use PM2 config).

### Phase 3: The Hands (MCP & Actions)
- [ ] **Task 3.1:** Set up `mcp-server-email` (Node.js) or a custom Python script to handle actual email sending via Gmail API.
- [ ] **Task 3.2:** Configure Claude Code `mcp.json` to recognize the Email tool.
- [ ] **Task 3.3:** Create `src/actions/linkedin_poster.py` (simulated API or basic Selenium/Playwright) to post approved text.

### Phase 4: The Brain (Orchestration)
- [ ] **Task 4.1:** Implement the "Orchestrator" loop (Python) that watches the `/Approved` folder and triggers the Action Layer.
- [ ] **Task 4.2:** Set up the "Ralph Wiggum" hook (or a loop script) to keep Claude working until `/Needs_Action` is empty.
- [ ] **Task 4.3:** Create a Cron/Schedule script for the "Monday Morning LinkedIn Draft".

### Phase 5: Verification
- [ ] **Task 5.1:** Test: Send an email to self -> Watcher catches it -> Claude drafts reply -> User approves -> Email sends.