# Skill: File Processor
---
description: Automatically processes files dropped in Inbox using Gemini AI reasoning.
---

## 🛠️ Capabilities
1. **Perception**: Detects new supported files (PDF, TXT, DOCX, etc.) in the `/Inbox` folder.
2. **Validation**: Validates file size (<10MB) and format compatibility.
3. **Reasoning**: Uses Gemini AI to understand file content and provide relevant answers/summaries.
4. **Action**: Appends AI responses directly to the source file and moves it to `/Done`.
5. **Memory**: Updates the Obsidian `Dashboard.md` with task status and duration.

## 📋 Usage
Simply drop any question in a `.txt` file into the `/Inbox` folder. The skill triggers automatically within 5 seconds.

## 🛡️ Safeguards
- Exponential backoff retry (3 attempts) for API errors.
- Automated error logging in `/Logs`.
- No file is ever permanently deleted (moved to `/Done` or kept in `/Inbox` on failure).
