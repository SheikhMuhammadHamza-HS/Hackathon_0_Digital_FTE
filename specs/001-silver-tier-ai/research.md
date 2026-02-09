# Research Findings

## Language & Runtime
- **Decision**: Python 3.10 (or newer) as the implementation language.
- **Rationale**: Existing codebase already uses Python 3.10+, and required libraries (watchdog, google‑generativeai, etc.) are stable on this version.
- **Alternatives considered**: Node.js, Go – rejected due to existing Python code and developer familiarity.

## Dependencies
- **watchdog** – file‑system monitoring (cross‑platform, proven reliability).
- **python‑dotenv** – securely load environment variables.
- **google‑generativeai** – Gemini API integration for AI processing.
- **requests** – HTTP client for potential future integrations.
- **pytest** – testing framework.
- **Rationale**: All are actively maintained, lightweight, and compatible with Python 3.10.

## Scheduling
- **Decision**: Use a simple cron‑like scheduler within the Python process (e.g., `schedule` library) to trigger weekly LinkedIn post generation.
- **Rationale**: Keeps the implementation lightweight; no external scheduler required.
- **Alternatives**: System cron, APScheduler – rejected for added complexity.

## Logging & Auditing
- **Decision**: JSON‑line logs written to `/Vault/Logs/YYYY-MM-DD.json` with rotating file handler.
- **Rationale**: Easy to query, satisfies audit requirements.
- **Retention**: 90 days (as clarified).

## Security
- **Decision**: Store secrets in `.env`, never write them to markdown files.
- **Rationale**: Aligns with constitutional requirement FR‑002.

All open questions have been resolved.
