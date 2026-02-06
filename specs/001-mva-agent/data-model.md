# Data Model: Minimum Viable Agent (Digital FTE)

## Core Entities

### File Metadata
**Purpose**: Represents metadata about files being processed by the agent
- **id**: UUID (primary identifier)
- **original_path**: String (absolute path to original file)
- **source_folder**: String (folder where file originated)
- **destination_folder**: String (where file will be moved upon completion)
- **file_size**: Integer (size in bytes, max 10MB per spec)
- **file_type**: String (determined from extension)
- **status**: Enum ['pending', 'processing', 'completed', 'failed']
- **created_at**: DateTime (timestamp when file was detected)
- **processed_at**: DateTime (timestamp when processing completed)
- **trigger_file_path**: String (path to corresponding trigger file)

### Trigger File
**Purpose**: Represents a detected file event that initiates processing
- **id**: UUID (corresponds to file metadata id)
- **filename**: String (TRIGGER_{timestamp}.md format)
- **type**: String (always "file_drop" for this agent)
- **source_path**: String (path to the file that triggered this)
- **timestamp**: DateTime (ISO-8601 format)
- **status**: Enum ['pending', 'processing', 'completed', 'failed']
- **location**: String (path to the trigger file in /Needs_Action)

### Dashboard Entry
**Purpose**: Represents a processed file in the dashboard
- **id**: UUID (reference to original file metadata)
- **display_name**: String (filename for display purposes)
- **timestamp**: DateTime (time when processing completed)
- **status**: String ('Done', 'Processing', 'Failed')
- **duration**: Float (time taken to process in seconds)
- **file_type**: String (file extension/type)

### Agent State
**Purpose**: Tracks the current operational state of the agent
- **id**: String (singleton "current_state")
- **status**: Enum ['idle', 'monitoring', 'processing', 'paused', 'error']
- **last_processed**: DateTime (timestamp of last processed file)
- **files_processed_today**: Integer (count of files processed today)
- **errors_count**: Integer (count of errors since last restart)
- **active_watchers**: List[String] (currently monitored directories)

## Relationships

### File Metadata ↔ Trigger File
- One-to-One relationship
- File metadata ID corresponds to trigger file ID
- Both represent the same logical file processing event

### File Metadata ↔ Dashboard Entry
- One-to-One relationship
- When file processing completes, a dashboard entry is created
- File metadata ID becomes the reference ID for the dashboard entry

### File Metadata ↔ Agent State
- One-to-Many relationship
- Agent state tracks aggregate information about file processing
- Individual file metadata contributes to agent state metrics

## Validation Rules

### File Metadata Validation
- file_size must be ≤ 10,485,760 bytes (10MB) as per specification
- status must be one of the defined enum values
- created_at must be a valid ISO-8601 datetime
- original_path must be a valid, existing file path

### Trigger File Validation
- filename must follow TRIGGER_{timestamp}.md pattern
- timestamp must be within 5 seconds of current time (to prevent stale triggers)
- status must transition appropriately (pending → processing → [completed|failed])

### Dashboard Entry Validation
- display_name must be non-empty string
- status must be one of defined values ('Done', 'Processing', 'Failed')
- duration must be positive number if processing completed

## State Transitions

### File Processing Lifecycle
```
Pending → Processing → Completed
      ↓         ↓
    Failed → Retrying → Completed
                ↓
              Failed (Final)
```

- Files start as 'pending' when detected in /Inbox
- Transition to 'processing' when Claude Code begins processing
- End as 'completed' on success or 'failed' after max retries

### Agent State Lifecycle
```
Idle → Monitoring → Processing → Idle
   ↑                    ↓
Paused ←----------- Error ←--- (from any state on error)
```

## Serialization Formats

### Trigger File Content Format
```yaml
---
type: "file_drop"
source_path: "path/to/original/file.pdf"
timestamp: "2026-02-06T10:00:00Z"
status: "pending"
---
## Context
File detected in Inbox.
```

### Dashboard Entry Format
The dashboard is a markdown table in `Dashboard.md`:
```markdown
# Agent Dashboard
| Time | Task | Status |
|------|------|--------|
| 10:00 | File1.pdf | Done |
| 10:05 | File2.docx | Done |
```