---
id: "002"
title: "Fix WhatsApp message extraction and task creation"
stage: "refactor"
date: "2026-02-16"
surface: "agent"
model: "claude-opus-4-6"
feature: "whatsapp"
branch: "001-silver-tier-ai"
user: "Claude user"
command: "Fix WhatsAppWatcher message extraction logic - ensure _get_unread_messages properly extracts content and _create_task_file is called"
labels: ["whatsapp", "playwright", "fix", "message-extraction"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - "src/watchers/whatsapp_watcher.py"
tests: []
---

## Prompt

User reported: WhatsAppWatcher detects unread messages but fails to extract content and create task files in Needs_Action folder. Logs show 'Processing potential unread chats' but no task is created.

Task requirements:
1. Fix _get_unread_messages logic to correctly click on chat with unread badge
2. Use robust selectors to extract last message text
3. Generate unique hash for each message to avoid duplicates
4. Ensure _create_task_file is called with extracted data (Sender, Message, Timestamp)
5. Save markdown file in ./Needs_Action for each new message

## Response snapshot

Rewrote `_get_unread_messages` with simpler, more robust approach:
1. Find chat list container first
2. Get all chat items and identify unread chats
3. Click on each chat and wait for it to load
4. Extract sender name from header
5. Find and parse message containers with multiple selector fallbacks
6. Extract text, timestamp, and generate unique hash
7. Return to chat list after processing

Fixed `_create_task_file`:
- Use `.get()` with defaults for all message fields
- Added detailed logging for created tasks
- Added traceback logging on failure

Key changes:
- Added debug logging throughout message extraction
- Fixed selector fallback logic
- Added fallback for when no unread badges found (check recent chats)
- Better error handling with traceback logging
- More robust message container detection

## Outcome

- ✅ Impact: WhatsApp message extraction now has detailed logging and robust fallback selectors
- 🧪 Tests: None added (run watcher to verify)
- 📁 Files: 1 modified (`src/watchers/whatsapp_watcher.py`)
- 🔁 Next prompts: Test the watcher to verify task files are created
- 🧠 Reflection: WhatsApp DOM changes frequently - need diagnostic screenshots on failure

## Evaluation notes (flywheel)

- Failure modes observed: Selectors breaking, chat navigation failing, message containers not found
- Graders run and results (PASS/FAIL): Not yet tested
- Prompt variant (if applicable): N/A
- Next experiment: Run watcher, check logs for detailed extraction steps
