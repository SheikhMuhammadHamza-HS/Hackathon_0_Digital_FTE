# Quickstart Guide: Minimum Viable Agent (Digital FTE)

## Prerequisites

- Python 3.10 or higher
- pip package manager
- Claude Code API access (requires API key)

## Setup

### 1. Clone or Create Project
```bash
# Navigate to your project directory
cd hackathon_zero
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

If requirements.txt doesn't exist yet, create it:
```bash
pip install watchdog python-dotenv requests pytest
pip freeze > requirements.txt
```

### 3. Configure Environment
Create a `.env` file in the project root:
```env
CLAUDE_CODE_API_KEY=your_claude_code_api_key_here
INBOX_PATH=./Inbox
NEEDS_ACTION_PATH=./Needs_Action
DONE_PATH=./Done
LOGS_PATH=./Logs
DASHBOARD_PATH=./Dashboard.md
COMPANY_HANDBOOK_PATH=./Company_Handbook.md
FILE_SIZE_LIMIT=10485760  # 10MB in bytes
MAX_RETRY_ATTEMPTS=3
```

Create an `.env.example` file for documentation:
```env
CLAUDE_CODE_API_KEY=your_claude_code_api_key_here
INBOX_PATH=./Inbox
NEEDS_ACTION_PATH=./Needs_Action
DONE_PATH=./Done
LOGS_PATH=./Logs
DASHBOARD_PATH=./Dashboard.md
COMPANY_HANDBOOK_PATH=./Company_Handbook.md
FILE_SIZE_LIMIT=10485760
MAX_RETRY_ATTEMPTS=3
```

### 4. Initialize Directory Structure
Run the setup command:
```bash
python -m src.cli.main setup
```

This creates:
- `/Inbox` - Where users drop files to be processed
- `/Needs_Action` - Where trigger files are created for processing
- `/Done` - Where processed files are moved
- `/Logs` - Where logs are stored
- `Dashboard.md` - Live dashboard showing processed files
- `Company_Handbook.md` - Ruleset file defining agent behaviors

## Usage

### Starting the Agent
```bash
python -m src.cli.main start
```

This starts the filesystem watcher and begins monitoring the `/Inbox` folder.

### Checking Status
```bash
python -m src.cli.main status
```

Shows current agent status and statistics.

### Stopping the Agent
```bash
python -m src.cli.main stop
```

Gracefully stops the filesystem watcher.

### Manual Processing
```bash
python -m src.cli.main process-trigger <trigger-file-path>
```

Manually process a specific trigger file.

## File Processing Flow

1. **User Action**: Drop file into `/Inbox` folder
2. **Detection**: Filesystem watcher detects new file within 5 seconds
3. **Trigger Creation**: Trigger file created in `/Needs_Action` with format `TRIGGER_{timestamp}.md`
4. **Processing**: Claude Code processes trigger file and updates `Dashboard.md`
5. **Completion**: Original file moved from `/Inbox` to `/Done` folder
6. **Dashboard Update**: Real-time update to `Dashboard.md` showing completion status

## Supported File Types

The agent supports:
- Documents: PDF, DOCX, TXT, XLSX, PPTX
- Images: JPG, PNG, GIF

Maximum file size: 10MB per file.

## Error Handling

- If processing fails, the system implements exponential backoff retry mechanism
- Maximum 3 retry attempts for transient failures
- After 3 failed attempts, file is moved to error queue for manual review
- All errors are logged in `/Logs` directory

## Testing

Run unit tests:
```bash
pytest tests/unit/
```

Run integration tests:
```bash
pytest tests/integration/
```

Run all tests:
```bash
pytest tests/
```

## Directory Structure
```
src/
├── agents/
│   ├── file_processor.py      # Claude Code integration
├── watchers/
│   └── filesystem_watcher.py  # Monitors /Inbox
├── models/
│   ├── file_metadata.py       # Data models
│   └── dashboard.py           # Dashboard management
├── services/
│   ├── file_mover.py          # Move files between folders
│   └── trigger_generator.py   # Create trigger files
├── cli/
│   └── main.py                # CLI entry point
└── utils/
    └── file_utils.py          # Helper functions

tests/
├── unit/
├── integration/
└── contract/
```