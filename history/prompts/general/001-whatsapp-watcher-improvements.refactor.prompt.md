---
id: "001"
title: "Improve WhatsApp Watcher anti-detection & selectors"
stage: "refactor"
date: "2026-02-16"
surface: "agent"
model: "claude-opus-4-6"
feature: "whatsapp"
branch: "001-silver-tier-ai"
user: "Claude user"
command: "check pending WhatsApp issues and make watcher bulletproof against detection and UI changes"
labels: ["whatsapp", "playwright", "anti-detection", "resilience"]
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

check the pending WhatsApp issues if you need whatsapp skill you can use it

User wants me to:
1. Check pending WhatsApp issues
2. Make the WhatsApp Watcher (Playwright-based) bulletproof against:
   - WhatsApp Web's anti-automation detection
   - UI changes (selectors breaking)
   - Session loss

## Response snapshot

Analyzed WhatsApp-related files:
- `src/watchers/whatsapp_watcher.py` - Main watcher implementation
- `src/agents/whatsapp_processor.py` - Message processing
- `mcp-servers/whatsapp-mcp/index.js` - MCP server for sending
- `.claude/skills/whatsapp-automation/SKILL.md` - WhatsApp automation skill

Identified issues:
1. API recipient list error (phone number not in allowed list)
2. Selector stability - WhatsApp Web frequently changes DOM selectors
3. Browser detection - anti-automation measures
4. No error recovery/auto-reconnect mechanism

Created improved WhatsAppWatcher with:
1. **Comprehensive stealth script** (16 anti-detection techniques)
2. **Selector fallback system** - Multiple selectors per element, auto-fallback
3. **Auto-reconnect** - Session validation, graceful degradation
4. **Health monitoring** - Consecutive error tracking, max retry logic
5. **Randomized timing** - Prevents pattern detection

## Outcome

- ✅ Impact: WhatsApp Watcher now resilient against detection and UI changes
- 🧪 Tests: None added (run watcher to test)
- 📁 Files: 1 modified (`src/watchers/whatsapp_watcher.py`)
- 🔁 Next prompts: Test the watcher, adjust selectors if needed
- 🧠 Reflection: WhatsApp Web selectors change frequently - need to make selector system extensible

## Evaluation notes (flywheel)

- Failure modes observed: Selectors breaking on WhatsApp Web updates, browser detection blocking access
- Graders run and results (PASS/FAIL): Not tested yet
- Prompt variant (if applicable): N/A
- Next experiment: Run watcher and capture any selector failures to update selector list
