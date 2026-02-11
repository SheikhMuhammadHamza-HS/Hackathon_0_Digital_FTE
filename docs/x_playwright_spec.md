# Technical Specification: X (Twitter) Browser Automation via Playwright

## 1. Overview
The objective is to implement a robust, browser-based automation script for posting tweets on X (Twitter). This system replaces the traditional API-based approach to bypass tier limitations and credit restrictions.

## 2. Technical Stack
- **Engine**: Playwright (Python)
- **Environment**: Windows / PowerShell (integrated with the Digital FTE Agent project)
- **Target URL**: `https://x.com`

## 3. Core Requirements

### 3.1 Filesystem Monitoring
The script must monitor the `d:\hackathon_zero\Approved` directory for specific tasks:
- **Identifier**: Target files where the header indicates `Platform: x` or `Platform: twitter`.
- **Pre-processing**: 
    - Strip YAML frontmatter (lines between `---`).
    - Remove metadata headers (e.g., `Subject:`, `To:`, `Platform:`).
    - Ensure the remaining text is within the character limit (typically 280 characters).

### 3.2 Browser Automation Logic
1. **Session Management**: Use a **Persistent Context** located at `d:\hackathon_zero\.playwright_session`. This ensures that once logged in manually, the session cookie is saved, bypassing 2FA on subsequent runs.
2. **Navigation**: Navigate to `https://x.com/compose/post` directly or locate the "Post" button on the home feed.
3. **Data Entry**: Inject the cleaned draft into the tweet composer text area using `fill()` or `type()`.
4. **Submission**: Click the "Post" button and wait for confirmation (e.g., a toast message or transition back to the feed).

### 3.3 State & Dashboard Management
After a posting attempt, the script must update the system state:
- **Success Case**:
    - Move the source file to `d:\hackathon_zero\Done`.
    - Append an entry to `d:\hackathon_zero\Dashboard.md`:
      `| [ISO-TIMESTAMP] | X/Twitter Post (Playwright) | SUCCESS |`
- **Failure Case**:
    - Move the source file to `d:\hackathon_zero\Failed`.
    - Capture a diagnostic screenshot to `d:\hackathon_zero\Logs\x_error.png`.
    - Append an entry to `d:\hackathon_zero\Dashboard.md`:
      `| [ISO-TIMESTAMP] | X/Twitter Post (Playwright) | FAILURE |`

## 4. Operational Guardrails
- **Latency**: Introduce random delays to mimic human typing speed and behavior.
- **Login Detection**: If the script detects it is not logged in, it should wait for the user to complete a manual login once to establish the persistent session.
