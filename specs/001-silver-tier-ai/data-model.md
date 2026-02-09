# Data Model

## Task File
- **Fields**:
  - `id` (UUID)
  - `source_type` (enum: email, filesystem)
  - `source_identifier` (email message‑ID or file path)
  - `created_at` (timestamp)
  - `metadata` (JSON blob – size, hash, etc.)
  - `status` (enum: pending, processing, completed, failed)

## Action Draft
- **Fields**:
  - `id` (UUID)
  - `task_id` (reference to Task File)
  - `action_type` (enum: email, linkedin)
  - `content` (draft body text)
  - `metadata` (JSON – recipient, subject, etc.)
  - `approval_status` (enum: pending, approved, rejected)

## Action Metadata (embedded in draft)
- `type` (email / linkedin)
- `to` (email address or LinkedIn audience identifier)
- `subject` (for email)
- `body` (content to send)

## Dashboard Entry
- `timestamp`
- `event_type` (e.g., task_created, draft_ready, action_executed)
- `details` (short description)

## Audit Log Entry
- `timestamp`
- `action` (read/write/execute)
- `resource` (file path or external API)
- `status` (success/failure)
- `details` (optional free‑text)

## Agent State
- `status` (idle, monitoring, processing, paused, error)
- `files_processed` (counter)
- `errors` (counter)
- `last_processed_at` (timestamp)
- `active_watchers` (list of watcher identifiers)
