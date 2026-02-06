# Minimum Viable Agent (Digital FTE)

A local-first "Digital FTE" agent that operates on a Perception → Reasoning → Memory loop to automate file processing tasks.

## Features

- Monitors an `/Inbox` folder for new files
- Automatically creates trigger files in `/Needs_Action`
- Processes files using Claude Code or Google Gemini integration
- Updates real-time `Dashboard.md` with processing status
- Moves processed files to `/Done` folder
- Cross-platform file monitoring with 5-second detection latency
- Comprehensive error handling with exponential backoff retry mechanism
- Security logging for all file processing events
- Real-time dashboard with chronological file processing records

## Supported File Types

- Documents: PDF, DOCX, TXT, XLSX, PPTX
- Images: JPG, PNG, GIF
- Maximum file size: 10MB

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Copy and configure environment:
   ```bash
   cp .env.example .env
   # Edit .env to add your Google Gemini API key (or Claude Code API key)
   ```

3. Initialize the agent:
   ```bash
   python -m src.cli.main setup
   ```

## Usage

Start the agent to begin monitoring:
```bash
python -m src.cli.main start
```

Check agent status:
```bash
python -m src.cli.main status
```

Stop the agent:
```bash
python -m src.cli.main stop
```

Manually process a trigger file:
```bash
python -m src.cli.main process-trigger --trigger-file-path /path/to/trigger/file.md
```

## Architecture

The agent implements a Perception → Reasoning → Memory loop:

1. **Perception**: Filesystem watcher detects new files in `/Inbox`
2. **Reasoning**: Claude Code processes trigger files and updates dashboard
3. **Memory**: Dashboard maintains record of processed files

## Directory Structure

- `/Inbox`: Files to be processed
- `/Needs_Action`: Trigger files for Claude Code
- `/Done`: Processed files
- `/Logs`: Log files
- `Dashboard.md`: Real-time processing status
- `Company_Handbook.md`: Agent behavior rules

## Configuration

All configuration is controlled through environment variables in `.env`:

- `CLAUDE_CODE_API_KEY`: Your Claude Code API key (optional)
- `GEMINI_API_KEY`: Your Google Gemini API key (preferred)
- `INBOX_PATH`: Directory to monitor for new files (default: `./Inbox`)
- `NEEDS_ACTION_PATH`: Directory for trigger files (default: `./Needs_Action`)
- `DONE_PATH`: Directory for processed files (default: `./Done`)
- `LOGS_PATH`: Directory for log files (default: `./Logs`)
- `DASHBOARD_PATH`: Path to dashboard file (default: `./Dashboard.md`)
- `COMPANY_HANDBOOK_PATH`: Path to company handbook (default: `./Company_Handbook.md`)
- `FILE_SIZE_LIMIT`: Maximum file size in bytes (default: 10485760 - 10MB)
- `MAX_RETRY_ATTEMPTS`: Maximum retry attempts for failed processing (default: 3)

## Testing

Run all tests:
```bash
python -m pytest tests/ -v
```

Run unit tests:
```bash
python -m pytest tests/unit/ -v
```

Run integration tests:
```bash
python -m pytest tests/integration/ -v
```

## Security

- All file access is logged for audit purposes
- File size limits prevent resource exhaustion
- Input validation protects against malicious filenames
- Encrypted API keys via environment variables

## Error Handling

- Automatic retry with exponential backoff for transient failures
- Failed processing attempts are logged for review
- Files that consistently fail are moved to error queue
- Comprehensive logging for debugging and monitoring

## Development

The project is organized into several modules:

- `src/agents/` - AI integration components
- `src/watchers/` - File system monitoring
- `src/models/` - Data structures and entities
- `src/services/` - Business logic
- `src/cli/` - Command-line interface
- `src/config/` - Configuration management
- `src/utils/` - Utility functions