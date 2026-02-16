---
id: "001"
title: "WhatsApp HITL Workflow Implementation"
stage: "green"
date: "2026-02-16"
surface: "agent"
model: "claude-opus-4-6"
feature: "whatsapp-automation"
branch: "001-silver-tier-ai"
user: "developer"
command: "review and implement WhatsApp HITL workflow"
labels: ["whatsapp", "hitl", "automation", "playwright", "mcp"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - src/watchers/whatsapp_watcher.py
  - src/agents/whatsapp_processor.py
  - src/agents/whatsapp_sender.py
  - src/services/action_executor.py
  - src/services/persistence_loop.py
tests:
  - Unit tests for WhatsApp processor metadata extraction
  - Integration test for end-to-end workflow
---

## Prompt

I need to implement a complete Human-in-the-Loop (HITL) workflow for WhatsApp message automation with the following requirements:

**System Architecture:**
- Technology: Python, Playwright for browser automation, Gemini AI for response generation
- Platform: WhatsApp Web automation
- Folders: Needs_Action, Pending_Approval, Approved, Done

**Required Workflow (End-to-End):**

1. **Message Detection & Capture (WhatsApp Watcher):**
   - When the persistence loop is running with an active WhatsApp Web session
   - Automatically detect incoming messages in real-time
   - Extract: Sender name, Message text, Timestamp
   - Create a markdown file in `./Needs_Action/` folder with format: `WHATSAPP_[timestamp]_[sender].md`
   - File should contain: type, sender, message content, metadata

2. **AI Processing (WhatsApp Processor):**
   - Monitor `./Needs_Action/` folder for new WhatsApp tasks
   - Parse the message content
   - Generate a contextual response using Gemini AI
   - Consider: Message tone, sender context, urgency
   - Create a draft response file in `./Pending_Approval/` folder
   - Draft should include: Original message reference, Proposed reply, Metadata for sending

3. **Human Approval (Manual Step):**
   - User reviews the draft in `./Pending_Approval/`
   - If approved, user moves/copies the file to `./Approved/` folder
   - System should detect this action

4. **Automated Sending (Action Executor):**
   - Monitor `./Approved/` folder for new approved responses
   - Parse the response file to extract: Recipient's WhatsApp number/ID, Message text to send
   - Send the message via WhatsApp Web (using Playwright automation)
   - After successful sending, move the file to `./Done/` folder
   - Log the action with timestamp and status

**Critical Requirements:**
- Ensure no duplicate processing (use message hashing)
- Handle errors gracefully (network issues, WhatsApp blocks, etc.)
- Maintain session persistence (avoid repeated QR scanning)
- Use anti-detection techniques for WhatsApp Web automation
- All file operations should be UTF-8 encoded to support emojis and Unicode
- Logging at each step for debugging

**Current Codebase Structure:**
- src/watchers/whatsapp_watcher.py - Message detection
- src/agents/whatsapp_processor.py - AI response generation
- src/agents/whatsapp_sender.py - Message sending
- src/services/action_executor.py - Orchestrates sending
- src/services/persistence_loop.py - Main loop monitoring folders

**What I Need:**
Please review and enhance the existing code to ensure all 4 steps work seamlessly together. Focus especially on:
1. Reliable message extraction from WhatsApp Web UI
2. Creating properly formatted task files
3. Ensuring the Action Executor correctly identifies WhatsApp tasks and sends messages
4. Error handling and retry mechanisms

Provide complete, working code for any files that need updates.

## Response snapshot

Implemented a complete HITL workflow for WhatsApp automation with the following enhancements:

### 1. WhatsApp Watcher (src/watchers/whatsapp_watcher.py)
- Added persistent message hashing to prevent duplicates across restarts
- Enhanced error handling with exponential backoff retry mechanism
- Improved message extraction with multiple selector fallbacks
- Added comprehensive logging at each step
- Fixed file naming to include sender information: `WHATSAPP_[timestamp]_[sender].md`
- Task files now include proper YAML frontmatter with metadata

### 2. WhatsApp Processor (src/agents/whatsapp_processor.py)
- Completely rewritten to properly parse WhatsApp-specific metadata
- Added `_extract_whatsapp_metadata()` method for robust YAML/content parsing
- Implemented `_analyze_message_tone()` for sentiment/urgency detection
- Created `_build_whatsapp_prompt()` for optimized Gemini prompts
- Added `_clean_draft_text()` to remove markdown artifacts from responses
- Generates contextual responses considering tone, urgency, and sender context

### 3. WhatsApp Sender (src/agents/whatsapp_sender.py)
- Implemented multi-mode sending: playwright, mcp, mock, auto
- Added `_send_via_playwright()` with direct browser automation
- Added `_send_via_new_playwright_session()` for standalone sending
- Implemented `_send_with_page_sync()` for reliable message sending
- Added rate limiting to prevent spam detection
- Included recipient validation
- Comprehensive error handling with fallback chains

### 4. Action Executor (src/services/action_executor.py)
- Enhanced platform detection with `extract_platform_header()`
- Added dedicated `_execute_whatsapp()` method with retry logic
- Implemented exponential backoff for transient failures
- Added validation before attempting to send
- Improved dashboard notifications for all platforms

### 5. Persistence Loop (src/services/persistence_loop.py)
- Fixed critical bug: was importing EmailProcessor instead of WhatsAppProcessor
- Added `_detect_task_type()` for robust task type detection
- Enhanced task type detection for linkedin, x/twitter platforms
- Added better error handling in processor imports
- Updated dashboard summary to include Pending_Approval counts

## Outcome

- ✅ Impact: Complete end-to-end HITL workflow for WhatsApp automation
- 🧪 Tests: Code reviewed for syntax errors and import consistency
- 📁 Files: 5 core files updated with enhanced functionality
- 🔁 Next prompts: Test the workflow with real WhatsApp Web session
- 🧠 Reflection: The key fix was correcting the processor import in persistence_loop.py which was preventing WhatsApp tasks from being processed correctly

## Evaluation notes (flywheel)

- Failure modes observed: Original code had incorrect processor import causing WhatsApp tasks to fail silently
- Graders run and results (PASS/FAIL): Syntax check PASS, Import resolution PASS
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Run integration test with actual WhatsApp Web to verify message extraction and sending
