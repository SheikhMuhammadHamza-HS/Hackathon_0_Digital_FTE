# Feature Specification: Personal AI Employee (Silver Tier)

**Feature Branch**: `001-silver-tier-ai`
**Created**: 2026-02-09
**Status**: Draft
**Input**: User description: "@01_silver_tier_spec.md"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Multi-Input Task Monitoring (Priority: P1)

A user wants their AI assistant to continuously monitor multiple input sources (Gmail inbox and local file system) for new tasks. When new items arrive, the system should automatically create task files in a central queue for processing, without requiring the user to manually check each source.

**Why this priority**: This is the foundation of the entire system. Without input monitoring, the AI has nothing to process. It enables the 24/7 operation capability that defines the Silver Tier.

**Independent Test**: Can be tested by dropping files into the monitored folder and sending test emails to Gmail. The system should automatically create task files in the Needs_Action folder within a defined time window, regardless of whether the rest of the system is implemented.

**Acceptance Scenarios**:

1. **Given** the system is monitoring the Inbox folder and Gmail, **When** a new file is dropped into Inbox, **Then** a task file is created in Needs_Action within 2 minutes with metadata about the source file
2. **Given** the system is monitoring Gmail, **When** a new email arrives marked as "Unread" and "Important", **Then** an email task file is created in Needs_Action within 2 minutes containing the email content and sender information
3. **Given** the monitoring system is running, **When** duplicate content is received, **Then** no duplicate task files are created
4. **Given** a file that exceeds size limits is dropped, **When** the file is processed, **Then** an error is logged and the file is moved to an error handling location

---

### User Story 2 - Automated Email Reply Drafting (Priority: P2)

When an email task arrives in the system, the AI should automatically read the email content, consult the company handbook for reply guidelines, and draft a professional reply. The draft should be saved to a Pending Approval folder for human review, not sent immediately.

**Why this priority**: This directly addresses the "Functional Assistant" value proposition - automating routine email responses while maintaining human oversight for sensitive actions.

**Independent Test**: Can be tested by placing an email task file in Needs_Action. The system should generate a draft reply in Pending_Approval that follows the tone and guidelines from Company_Handbook.md, without requiring any external email sending capability.

**Acceptance Scenarios**:

1. **Given** an email task file in Needs_Action, **When** the system processes the task, **Then** a reply draft is created in Pending_Approval following company guidelines
2. **Given** the Company_Handbook.md contains specific tone instructions, **When** the draft is generated, **Then** the reply matches the specified tone (e.g., professional, friendly, formal)
3. **Given** an email requiring information not available, **When** the draft is generated, **Then** the draft includes placeholders or questions for human clarification
4. **Given** an email task is processed, **When** the draft is created, **Then** the original email content is referenced in the draft for context

---

### User Story 3 - Social Media Content Creation (Priority: P3)

The user wants the AI to periodically create LinkedIn posts about business updates. On a scheduled basis (e.g., every Monday morning), the system should read recent business goals and project updates, then draft a professional LinkedIn post and save it to Pending Approval for human review.

**Why this priority**: This supports the business growth goals (as defined in Business_Goals.md) by automating content marketing while maintaining human control over what gets published.

**Independent Test**: Can be tested by triggering the scheduled task manually. The system should read Business_Goals.md or other project documentation and create a LinkedIn post draft in Pending_Approval, without requiring actual LinkedIn posting capability.

**Acceptance Scenarios**:

1. **Given** the scheduled task triggers, **When** the system generates a LinkedIn post, **Then** a draft is created in Pending_Approval containing recent business updates
2. **Given** Business_Goals.md contains specific metrics or achievements, **When** the post is drafted, **Then** these achievements are highlighted professionally
3. **Given** no new updates are available, **When** the scheduled task runs, **Then** a post is still created with evergreen content or a status update
4. **Given** multiple recent updates exist, **When** the post is drafted, **Then** it highlights the most significant achievements without being overwhelming

---

### User Story 4 - Human-in-the-Loop Approval Execution (Priority: P1)

When a user reviews and approves a draft in Pending_Approval by moving it to the Approved folder, the system should detect this action, parse the draft for action metadata, execute the appropriate action (send email, post to LinkedIn), and move the file to Done upon successful completion.

**Why this priority**: This is the critical safety mechanism that ensures sensitive actions (sending emails, posting to social media) never execute without explicit human approval. It's a core constitutional requirement.

**Independent Test**: Can be tested by manually moving a properly formatted draft from Pending_Approval to Approved. The system should detect the move, parse the action metadata, execute the action, and move the file to Done.

**Acceptance Scenarios**:

1. **Given** an email draft in Pending_Approval with action metadata, **When** the user moves it to Approved, **Then** the email is sent and the file moves to Done
2. **Given** a LinkedIn post draft in Pending_Approval, **When** the user moves it to Approved, **Then** the post is published and the file moves to Done
3. **Given** a draft is moved to Approved but execution fails, **When** the error occurs, **Then** the file remains in Approved with error details logged
4. **Given** a draft without valid action metadata is moved to Approved, **When** the system processes it, **Then** an error is logged and no action is taken

---

### User Story 5 - Real-Time Dashboard Updates (Priority: P2)

The user wants a central dashboard that provides real-time visibility into the system's status, including counts of pending tasks, items awaiting approval, recent processing activity, and key business metrics like simulated bank balance.

**Why this priority**: This provides transparency and confidence in the system's operation, allowing the user to monitor progress and identify issues without diving into log files.

**Independent Test**: Can be tested by triggering system events (adding files, processing tasks, approving actions) and verifying that the Dashboard.md file updates with accurate information in near real-time.

**Acceptance Scenarios**:

1. **Given** the system starts up, **When** initialization completes, **Then** Dashboard.md displays current system status including monitoring state
2. **Given** a new task is added to Needs_Action, **When** the change occurs, **Then** Dashboard.md updates the pending tasks count within 10 seconds
3. **Given** a draft is added to Pending_Approval, **When** the change occurs, **Then** Dashboard.md lists the new draft awaiting review
4. **Given** an action is completed successfully, **When** the file moves to Done, **Then** Dashboard.md records the completion with timestamp and result

---

### Edge Cases

- What happens when the Gmail API fails to authenticate or becomes unavailable?
- How does system handle files in the Inbox folder that are corrupt or unreadable?
- What occurs when multiple files are dropped simultaneously?
- How does system behave when Pending_Approval folder has no drafts during scheduled LinkedIn posting?
- What happens when a user moves a file to Approved but action execution takes longer than timeout period?
- How does system handle duplicate emails from the same thread?
- What occurs when Company_Handbook.md is missing or contains conflicting guidelines?
- What happens when the system runs out of disk space for logging?
- How does system behave when user manually modifies files while processing?
- What occurs when network connectivity is lost during external action execution?

## Requirements *(mandatory)*

### Functional Requirements

#### Constitutional Requirements (Non-Negotiable)

- **FR-001**: System MUST keep all user data, logs, and task states in local storage (Obsidian Vault). Data may leave the machine only when explicitly required for an external action (e.g., sending an email).
- **FR-002**: System MUST NEVER write API keys, passwords, or tokens into Markdown files. All secrets must be stored in `.env` file listed in `.gitignore`.
- **FR-003**: System MUST NOT perform "Sensitive Actions" (sending emails, posting to LinkedIn, deleting files) without explicit human approval. The approval mechanism requires creating a file in `/Pending_Approval` and waiting for the human to move it to `/Approved`.
- **FR-004**: System MUST log every action taken (read, write, execute) in `/Vault/Logs/YYYY-MM-DD.json` as an audit trail.
- **FR-005**: System MUST ensure tasks are fully completed before exiting, using a completion verification mechanism to prevent partial execution.

#### Input Monitoring Requirements

- **FR-006**: System MUST monitor Gmail inbox for new messages marked as "Unread" and "Important" at least every 2 minutes.
- **FR-007**: System MUST monitor the local `/Inbox` folder for new files and process them within 2 minutes of arrival.
- **FR-008**: System MUST create task files in `/Needs_Action` for each detected input (email or file) with appropriate metadata.
- **FR-009**: System MUST validate file size (maximum 10MB) and file type before processing files from `/Inbox`.
- **FR-010**: System MUST avoid creating duplicate task files for the same content source using content-based hashing (hash of email body or file content).

#### Email Processing Requirements

- **FR-011**: System MUST read email content from task files created by the Gmail watcher.
- **FR-012**: System MUST consult `Company_Handbook.md` for reply guidelines when drafting email responses.
- **FR-013**: System MUST draft email replies and save them to `/Pending_Approval` folder with action metadata.
- **FR-014**: System MUST NOT send emails immediately after drafting; sending only occurs after human approval.
- **FR-015**: Email drafts MUST include the original email content reference for context.

#### Social Media Requirements

- **FR-016**: System MUST support scheduled task execution for periodic activities (e.g., LinkedIn post creation).
- **FR-017**: System MUST read `Business_Goals.md` or recent project updates when generating LinkedIn content.
- **FR-018**: System MUST draft professional LinkedIn posts and save them to `/Pending_Approval` folder with action metadata.
- **FR-019**: LinkedIn posts MUST NOT be published immediately after drafting; publishing only occurs after human approval.

#### Approval and Execution Requirements

- **FR-020**: System MUST detect when files are moved from `/Pending_Approval` to `/Approved` folder.
- **FR-021**: System MUST parse approved files for Action Metadata including Type (Email/Post), To (recipient), and Body (content).
- **FR-022**: System MUST execute the appropriate action (email send or LinkedIn post) based on the action metadata.
- **FR-023**: System MUST move files to `/Done` folder upon successful action execution.
- **FR-024**: System MUST log execution results to `/Vault/Logs` with timestamp and status.

#### Dashboard Requirements

- **FR-025**: System MUST update `Dashboard.md` on system startup or task completion.
- **FR-026**: Dashboard MUST display the current bank balance (simulated or read from CSV).
- **FR-027**: Dashboard MUST display the count of files in `/Needs_Action` folder.
- **FR-028**: Dashboard MUST display the list of items in `/Pending_Approval` folder.
- **FR-029**: Dashboard MUST display recent processing activity with timestamps.

#### Error Handling Requirements

- **FR-030**: System MUST log all errors with sufficient detail for troubleshooting.
- **FR-031**: System MUST continue operating when individual task processing fails without crashing.
- **FR-032**: System MUST retry failed external actions (email sending, LinkedIn posting) up to 3 times with exponential backoff.
- **FR-033**: System MUST move failed files to an error handling location or mark them with error status.

#### Security Requirements

- **FR-034**: System MUST validate file paths to prevent directory traversal attacks.
- **FR-035**: System MUST NOT permanently delete files; deleted files should be moved to a `.trash` directory.
- **FR-036**: System MUST validate action metadata before execution to prevent unauthorized actions.
- **FR-037**: System MUST log security events (file access, processing, encryption events) separately.

### Key Entities

- **Task File**: Represents an item needing processing, created in `/Needs_Action` from email or file input. Contains metadata (source type, timestamp, original content) and processing status.

- **Action Draft**: Represents a pending action (email reply or LinkedIn post) created by the AI and saved in `/Pending_Approval`. Contains the content to be sent/posted plus action metadata (type, recipient, etc.) and approval status.

- **Action Metadata**: Structured information embedded in draft files that describes what action to take. Includes Type (Email/LinkedIn), To (recipient address or platform), Body (content to send), Subject (for emails), and any additional parameters.

- **Dashboard Entry**: Represents a single event or status update displayed in `Dashboard.md`. Contains timestamp, event type, status, and relevant details. Used to provide real-time visibility into system operations.

- **Audit Log Entry**: Represents a logged action in `/Vault/Logs/YYYY-MM-DD.json`. Contains timestamp, action type (read/write/execute), affected file or resource, status (success/failure), and any additional context.

- **Agent State**: Represents the current operational state of the system. Contains status (Idle, Monitoring, Processing, Paused, Error), files processed count, error count, last processed timestamp, and active watchers list.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: System detects and creates task files for new inputs (Gmail emails or local files) within 2 minutes of arrival 95% of the time.

- **SC-002**: User can review an email draft and approve it by moving a single file from Pending_Approval to Approved, with the email successfully sent within 30 seconds of approval.

- **SC-003**: System generates and saves LinkedIn post drafts to Pending_Approval on the scheduled day (e.g., Monday) by 10:00 AM 90% of the time.

- **SC-004**: Dashboard reflects the current system state (pending tasks, awaiting approval, recent activity) within 10 seconds of any state change.

- **SC-005**: System maintains a complete audit trail of all actions (read, write, execute) in date-organized log files with 100% coverage of actions taken.

- **SC-006**: System continues operating without manual intervention for at least 24 hours, processing all incoming tasks and maintaining accurate state.

- **SC-007**: No sensitive actions (email sending, LinkedIn posting) execute without human approval - 0 false positives over 100 test cases.

- **SC-008**: System successfully recovers from temporary failures (Gmail API timeout, network loss) and continues processing without human intervention 95% of the time.

## Assumptions

- User has Gmail account with API access enabled.
- User has LinkedIn account with posting capabilities.
- System runs on a machine with persistent local storage (Obsidian Vault).
- User has permission to send emails and post to LinkedIn on behalf of their account.
- Network connectivity is available for external actions (Gmail API, LinkedIn).
- Company_Handbook.md contains sufficient guidance for the AI to generate appropriate responses.
- Business_Goals.md contains up-to-date information for LinkedIn post content.
- User understands and accepts the approval workflow for sensitive actions.
- System clock is synchronized for accurate timestamps and scheduling.

## Clarifications

### Session 2026-02-09

- Q: What is the exact schedule for LinkedIn post generation? → A: Every Monday at 9:00 AM

## Out of Scope

- Advanced natural language understanding beyond standard email and document processing.
- Machine learning model training or customization.
- Multi-user support or permissions management.
- Advanced scheduling beyond simple cron-like periodic tasks.
- Integration with other social media platforms beyond LinkedIn.
- Real-time chat or conversational interface with the AI.
- Mobile or web-based user interfaces.
- Cloud deployment or remote access capabilities.
- Advanced analytics or reporting beyond the dashboard.
- Support for processing very large files (>10MB) or streaming content.
- Voice input or output capabilities.