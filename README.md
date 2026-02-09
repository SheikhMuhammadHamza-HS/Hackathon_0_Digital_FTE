# Personal AI Employee (Silver Tier)

A local-first "Digital FTE" agent that automates email drafting, LinkedIn posting, and task management through a human-in-the-loop approval workflow.

## Features

### Core Capabilities
- **File Monitoring**: Monitors `/Inbox` folder and Gmail inbox for new tasks
- **Automated Email Drafting**: Reads email tasks, consults `Company_Handbook.md`, drafts replies
- **LinkedIn Content Creation**: Weekly scheduled LinkedIn posts based on `Business_Goals.md`
- **Human-in-the-Loop Approval**: Drafts placed in `/Pending_Approval` for review
- **Action Execution**: Approved drafts automatically sent/posted
- **Real-Time Dashboard**: `Dashboard.md` shows chronological system events
- **Security Logging**: All file access and processing events logged

### Supported Platforms
- Email: Gmail API integration
- LinkedIn: API-based posting
- File-based workflows

## Setup

### Prerequisites
- Python 3.10 or higher
- pip (Python package manager)

### Dependencies

The system requires the following Python packages:
- `watchdog==3.0.0` - File system monitoring
- `python-dotenv==1.0.0` - Environment variable management
- `requests==2.31.0` - HTTP library
- `schedule==1.2.0` - Job scheduling
- `pytest==7.4.3` - Testing framework
- `google-generativeai==0.8.6` - Google Gemini AI integration

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd hackathon_zero
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and paths
   ```

4. **Initialize the agent**:
   ```bash
   python -m src.cli.main setup
   ```

5. **Run system validation**:
   ```bash
   python scripts/validate_system.py
   ```

For detailed configuration instructions, see [docs/setup.md](docs/setup.md).

## Usage

### Start the Agent

Run all watchers and services:
```bash
python -m src.cli.main start
```

### Individual Components

Start file watcher only:
```bash
python -m src.cli.main watch-inbox
```

Start Gmail watcher:
```bash
python -m src.cli.main watch-gmail
```

Start approval watcher:
```bash
python -m src.cli.main watch-approval
```

Start scheduler for LinkedIn posts:
```bash
python -m src.cli.main schedule-start
```

### Draft Management

Process email tasks and create drafts:
```bash
python -m src.cli.main email-draft
```

Create LinkedIn drafts from Business Goals:
```bash
python -m src.cli.main linkedin-draft
```

Trigger scheduled draft immediately:
```bash
python -m src.cli.main schedule-run
```

### Status and Management

Check agent status:
```bash
python -m src.cli.main status
```

View dashboard:
```bash
python -m src.cli.main dashboard
```

Stop all services:
```bash
python -m src.cli.main stop
```

## Architecture

### System Overview

```
                    ┌─────────────────────────────────────┐
                    │          CLI Commands               │
                    └─────────────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │                                   │
            ┌───────▼────────┐              ┌──────────▼──────────┐
            │  File Watcher  │              │   Gmail Watcher     │
            └───────┬────────┘              └──────────┬──────────┘
                    │                                   │
                    └─────────────────┬─────────────────┘
                                      │
                              ┌───────▼────────┐
                              │ Task Generator │
                              └───────┬────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │                                   │
            ┌───────▼────────┐              ┌──────────▼──────────┐
            │ Email Processor│              │ LinkedIn Processor  │
            └───────┬────────┘              └──────────┬──────────┘
                    │                                   │
                    └─────────────────┬─────────────────┘
                                      │
                              ┌───────▼────────┐
                              │  Draft Store   │
                              └───────┬────────┘
                                      │
                              ┌───────▼────────┐
                              │ Pending_Approval│
                              └───────┬────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │                                   │
            ┌───────▼────────┐              ┌──────────▼──────────┐
            │Approval Watcher│              │  Action Executor    │
            └───────┬────────┘              └──────────┬──────────┘
                    │                                   │
                    └─────────────────┬─────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │                                   │
            ┌───────▼────────┐              ┌──────────▼──────────┐
            │  Email Sender  │              │ LinkedIn Poster     │
            └───────┬────────┘              └──────────┬──────────┘
                    │                                   │
                    └─────────────────┬─────────────────┘
                                      │
                              ┌───────▼────────┐
                              │   Dashboard    │
                              └────────────────┘
```

### Directory Structure

```
hackathon_zero/
├── Inbox/                    # Input files for processing
├── Needs_Action/             # Generated task files
├── Pending_Approval/         # Drafts awaiting review
├── Approved/                 # Approved drafts for execution
├── Done/                     # Completed tasks
├── Failed/                   # Failed operations
├── Logs/                     # Audit logs
├── Vault/                    # Secure storage
├── Dashboard.md              # Real-time system status
├── Business_Goals.md         # Business metrics for LinkedIn
├── Company_Handbook.md       # Email reply guidelines
├── src/
│   ├── agents/               # AI integration
│   │   ├── email_processor.py
│   │   ├── email_sender.py
│   │   ├── file_processor.py
│   │   ├── linkedin_processor.py
│   │   └── linkedin_poster.py
│   ├── watchers/             # File/email monitoring
│   │   ├── approval_watcher.py
│   │   ├── filesystem_watcher.py
│   │   └── gmail_watcher.py
│   ├── services/             # Business logic
│   │   ├── action_executor.py
│   │   ├── dashboard_updater.py
│   │   ├── draft_store.py
│   │   ├── scheduler.py
│   │   └── task_generator.py
│   ├── models/               # Data structures
│   ├── cli/                  # Command interface
│   ├── config/               # Configuration
│   └── utils/                # Utilities
├── tests/                    # Test suite
├── docs/                     # Documentation
└── scripts/                  # Utility scripts
```

## Configuration

All configuration is controlled through environment variables in `.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google Gemini API key | Required |
| `GMAIL_API_KEY` | Gmail API key | Optional |
| `LINKEDIN_API_KEY` | LinkedIn API key | Optional |
| `INBOX_PATH` | Input folder | `./Inbox` |
| `NEEDS_ACTION_PATH` | Task files folder | `./Needs_Action` |
| `PENDING_APPROVAL_PATH` | Drafts folder | `./Pending_Approval` |
| `APPROVED_PATH` | Approved folder | `./Approved` |
| `DONE_PATH` | Completed folder | `./Done` |
| `FAILED_PATH` | Failed folder | `./Failed` |
| `LOGS_PATH` | Logs folder | `./Logs` |
| `DASHBOARD_PATH` | Dashboard file | `./Dashboard.md` |
| `COMPANY_HANDBOOK_PATH` | Handbook file | `./Company_Handbook.md` |
| `BUSINESS_GOALS_PATH` | Business goals file | `./Business_Goals.md` |
| `FILE_SIZE_LIMIT` | Max file size (bytes) | `10485760` |
| `MAX_RETRY_ATTEMPTS` | Retry attempts | `3` |

## Testing

Run all tests:
```bash
pytest -q
```

Run specific test suites:
```bash
pytest tests/unit/ -v          # Unit tests
pytest tests/integration/ -v   # Integration tests
```

Run with coverage:
```bash
pytest --cov=src tests/
```

## Security

- API keys stored in environment variables only
- No secrets logged (verified in `logging_config.py`)
- File path validation prevents directory traversal
- All file access logged for audit
- Input validation on all user inputs

## Error Handling

- Exponential backoff for transient failures
- Failed operations moved to `/Failed` folder
- Comprehensive logging for debugging
- Graceful degradation when APIs unavailable

## Troubleshooting

### Common Issues

1. **Dashboard not updating**: Check file permissions and disk space
2. **API failures**: Verify API keys in `.env`
3. **Watchers not detecting files**: Check folder paths and permissions
4. **Scheduler not running**: Verify schedule library is installed

### Logs

Check logs in `/Logs` directory for detailed error information:
```bash
tail -f Logs/$(date +%Y-%m-%d).log
```

## Development

### Code Style
- Follow PEP 8 guidelines
- Use type hints where appropriate
- Write docstrings for all public methods

### Contributing
1. Write tests for new features
2. Update documentation
3. Ensure all tests pass before committing

## License

See LICENSE file for details.