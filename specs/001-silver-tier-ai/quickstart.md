# Quickstart Guide

## Prerequisites
- Python 3.10+ installed
- Install dependencies: `pip install -r requirements.txt`
- Create a `.env` file with `GEMINI_API_KEY` and `CLAUDE_CODE_API_KEY`

## Setup
```bash
# Clone repository (if not already)
git clone <repo-url>
cd hackathon_zero

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install Python packages
pip install -r requirements.txt
```

## Running the Agent
```bash
python src/cli/main.py start
```
The agent will begin monitoring Gmail and the local `Inbox` folder, creating task files in `Needs_Action`.

## Approving Drafts
1. Review drafts created in `Pending_Approval`.
2. When ready, move the draft file to the `Approved` folder.
3. The agent will automatically execute the action (send email or post to LinkedIn) and move the file to `Done`.

## Dashboard
Open `Dashboard.md` to see real‑time status, pending tasks, and recent activity.

## Stopping the Agent
Press `Ctrl+C` in the terminal running the agent, or run:
```bash
python src/cli/main.py stop
```

For more detailed instructions, see the full documentation in `README.md`.
