# Gold Tier Specification — Personal AI Employee Hackathon
**Version:** 1.0  
**Tier:** Gold  
**Base:** Silver Tier Complete  
**Development Approach:** Spec-Driven Development

---

## 1. Project Overview

Build a fully autonomous AI Employee that manages personal and business affairs 24/7 using Claude Code as the reasoning engine and Obsidian as the local dashboard. Gold Tier extends Silver by adding full cross-domain integration, Odoo accounting, multi-platform social media, weekly CEO briefing, Ralph Wiggum loop, and comprehensive error recovery.

---

## 2. Vault Structure

```
AI_Employee_Vault/
├── Dashboard.md                    # Real-time system overview
├── Company_Handbook.md             # Rules of engagement for Claude
├── Business_Goals.md               # Q1 targets, KPIs, thresholds
├── Needs_Action/                   # Watchers write here
├── In_Progress/                    # Claimed tasks (prevent double-work)
├── Plans/                          # Claude-generated Plan.md files
├── Pending_Approval/               # HITL approval requests
├── Approved/                       # Human-approved actions
├── Rejected/                       # Human-rejected actions
├── Done/                           # Completed tasks
├── Logs/                           # Audit logs YYYY-MM-DD.json
├── Briefings/                      # Monday CEO briefings
├── Invoices/                       # Generated invoice files
├── Accounting/
│   ├── Rates.md                    # Client pricing rates
│   ├── Bank_Transactions.md        # Bank activity log
│   └── Current_Month.md            # Monthly transaction summary
├── Clients/                        # Per-client markdown files
└── Tasks/
    └── Done/                       # Completed weekly tasks
```

---

## 3. Architecture

### 3.1 Four-Layer System

```
PERCEPTION → REASONING → ACTION → PERSISTENCE
```

| Layer | Component | Technology |
|-------|-----------|------------|
| Perception | Watcher Scripts | Python |
| Reasoning | Claude Code | claude-opus-4-5 |
| Action | MCP Servers | Node.js |
| Persistence | Ralph Wiggum Loop | Stop Hook |

### 3.2 Data Flow

```
External Source (Gmail/WhatsApp/Bank/Social)
        ↓
Watcher Script detects event
        ↓
Creates .md file in /Needs_Action/
        ↓
Orchestrator.py triggers Claude Code
        ↓
Claude reads → thinks → writes Plan.md
        ↓
Sensitive action? → /Pending_Approval/
Non-sensitive?   → MCP executes directly
        ↓
Human moves file to /Approved/
        ↓
Orchestrator triggers MCP action
        ↓
Task moved to /Done/ + Log written
        ↓
Dashboard.md updated
```

---

## 4. Required Claude Code Skills

All AI functionality must be implemented as Agent Skills inside `.claude/skills/`.

### 4.1 Skill List

| # | Skill Name | Depends On |
|---|-----------|------------|
| 1 | invoice-generator | — |
| 2 | facebook-automation | — |
| 3 | instagram-automation | — |
| 4 | odoo-accounting-mcp | — |
| 5 | invoice-processor | odoo-accounting-mcp |
| 6 | payment-tracker | odoo-accounting-mcp |
| 7 | financial-reporting | odoo-accounting-mcp, payment-tracker |
| 8 | x-twitter-automation | — |
| 9 | tweet-thread-generator | x-twitter-automation |
| 10 | social-listener | — |
| 11 | error-recovery-manager | — |
| 12 | circuit-breaker | — |
| 13 | health-monitor | — |
| 14 | weekly-audit-generator | odoo-accounting-mcp, financial-reporting, payment-tracker, social-listener |

### 4.2 Skill Structure

```
.claude/
└── skills/
    └── <skill-name>/
        └── SKILL.md
```

Each SKILL.md contains:
- YAML frontmatter (name, description)
- Purpose
- Capabilities
- Input sources
- Output format
- HITL rules
- Error handling
- Dependencies

---

## 5. Watcher Scripts

### 5.1 Required Watchers

| Watcher | Trigger | Output File |
|---------|---------|-------------|
| gmail_watcher.py | Unread important emails | /Needs_Action/EMAIL_<id>.md |
| whatsapp_watcher.py | Keywords: urgent, invoice, payment, help | /Needs_Action/WHATSAPP_<id>.md |
| filesystem_watcher.py | File dropped in /Inbox/ | /Needs_Action/FILE_<name>.md |
| finance_watcher.py | New bank transactions | /Accounting/Bank_Transactions.md |
| social_listener.py | Brand mentions on all platforms | /Needs_Action/MENTION_<platform>_<date>.md |

### 5.2 Base Watcher Pattern

All watchers extend BaseWatcher:
- `check_for_updates()` — polls source, returns new items
- `create_action_file()` — writes .md to /Needs_Action/
- `run()` — infinite loop with configurable check_interval
- Exception handling with logging (never crashes silently)

### 5.3 Process Management

All watchers must run via PM2:

```bash
pm2 start gmail_watcher.py --interpreter python3
pm2 start whatsapp_watcher.py --interpreter python3
pm2 start finance_watcher.py --interpreter python3
pm2 start social_listener.py --interpreter python3
pm2 save && pm2 startup
```

---

## 6. MCP Server Configuration

### 6.1 Required MCP Servers

| Server | Capability | Use Case |
|--------|-----------|---------|
| filesystem | Read, write, list files | Vault operations |
| email-mcp | Send, draft, search emails | Gmail integration |
| browser-mcp | Navigate, click, fill forms | Payment portals |
| calendar-mcp | Create, update events | Scheduling |

### 6.2 Config File

Location: `~/.config/claude-code/mcp.json`

```json
{
  "servers": [
    {
      "name": "email",
      "command": "node",
      "args": ["/path/to/email-mcp/index.js"],
      "env": {
        "GMAIL_CREDENTIALS": "/path/to/credentials.json"
      }
    },
    {
      "name": "browser",
      "command": "npx",
      "args": ["@anthropic/browser-mcp"],
      "env": {
        "HEADLESS": "true"
      }
    }
  ]
}
```

---

## 7. Odoo Community Integration

### 7.1 Requirements

- Odoo 19+ Community Edition (self-hosted, local)
- JSON-RPC API enabled
- Modules: Accounting, Invoicing

### 7.2 Connection Spec

```
Endpoint : http://localhost:8069/jsonrpc
Auth     : username + password via XML-RPC
Models   : account.move, account.payment, res.partner
```

### 7.3 Draft-Only Rule

Claude NEVER posts or confirms any Odoo entry without a corresponding `/Approved/` file present. All Odoo writes are draft-only until human approves.

### 7.4 Invoice Flow in Odoo

```
1. Read client from /Clients/<name>.md
2. Read rate from /Accounting/Rates.md
3. Create draft invoice in Odoo (move_type=out_invoice)
4. Write /Pending_Approval/INVOICE_<client>_<date>.md
5. Human moves file to /Approved/
6. Orchestrator detects → posts invoice in Odoo
7. Logs to /Logs/YYYY-MM-DD.json
8. Moves task to /Done/
```

---

## 8. Social Media Integration

### 8.1 Platform Coverage

| Platform | Actions | API |
|----------|---------|-----|
| LinkedIn | Post, engagement summary | LinkedIn API |
| Facebook | Post to Page, monitor comments | Meta Graph API |
| Instagram | Post image+caption, hashtags, metrics | Meta Graph API |
| Twitter/X | Tweet, thread, monitor mentions | X API v2 |

### 8.2 HITL Rules for Social

| Action | Approval Required |
|--------|------------------|
| Scheduled posts | No — auto-post allowed |
| Replies to mentions | Yes — always |
| DMs | Yes — always |
| New platform connections | Yes — always |

### 8.3 Tweet Thread Generator Spec

- Source: Plan.md or /Needs_Action/ file
- Max 280 chars per tweet
- Format: numbered (1/n, 2/n)
- Tweet 1: hook (question or bold statement)
- Tweet 2 to n-1: content points
- Last tweet: CTA + hashtags
- Space between posts: 30 seconds (rate limit safe)
- Output: /Pending_Approval/THREAD_<topic>_<date>.md

### 8.4 Social Listener Spec

- Check interval: every 30 minutes
- Keywords from: `BRAND_KEYWORDS` env variable
- Sentiment: positive / negative / neutral
- Negative → /Needs_Action/ immediately
- Question → /Needs_Action/ within 1 hour
- Positive → log only, no action

---

## 9. Human-in-the-Loop (HITL)

### 9.1 Approval File Format

```markdown
---
type: approval_request
action: <action_type>
amount: <if_financial>
recipient: <target>
reason: <why>
created: <ISO_timestamp>
expires: <ISO_timestamp>
status: pending
---

## Details
[Action details here]

## To Approve
Move this file to /Approved/

## To Reject
Move this file to /Rejected/
```

### 9.2 Permission Boundaries

| Action Category | Auto-Approve | Always Require Approval |
|----------------|-------------|------------------------|
| Email replies | To known contacts | New contacts, bulk sends |
| Payments | < $50 recurring | All new payees, > $100 |
| Social media | Scheduled posts | Replies, DMs |
| File operations | Create, read | Delete, move outside vault |
| Odoo entries | None | All posts/confirmations |

---

## 10. Ralph Wiggum Loop

### 10.1 Purpose

Keeps Claude iterating on a multi-step task until completion instead of stopping after one pass.

### 10.2 How It Works

```
1. Orchestrator creates state file with prompt
2. Claude works on task
3. Claude tries to exit
4. Stop hook checks: Is task file in /Done/?
5. YES → allow exit (complete)
6. NO  → block exit, re-inject prompt, loop continues
7. Repeat until complete or max iterations reached
```

### 10.3 Usage

```bash
/ralph-loop "Process all files in /Needs_Action, move to /Done when complete" \
--completion-promise "TASK_COMPLETE" \
--max-iterations 10
```

### 10.4 Completion Strategies

| Strategy | Method | Use Case |
|----------|--------|---------|
| Promise-based | Claude outputs `<promise>TASK_COMPLETE</promise>` | Simple tasks |
| File movement | Stop hook detects file moved to /Done/ | Complex multi-step (Gold) |

---

## 11. Weekly CEO Briefing

### 11.1 Trigger

- Cron: Every Sunday at 11:00 PM
- Manual: Drop AUDIT_REQUEST.md into /Needs_Action/

```cron
0 23 * * 0   weekly-audit-generator
```

### 11.2 Data Sources

| Source | Data |
|--------|------|
| Business_Goals.md | Targets, KPIs, alert thresholds |
| Odoo JSON-RPC | Invoices, payments, balances |
| Bank_Transactions.md | All bank activity this week |
| /Tasks/Done/ | Completed tasks + time taken |
| /Logs/ | All AI actions this week |
| social-listener | Engagement metrics per platform |

### 11.3 Output File

Location: `/Briefings/YYYY-MM-DD_Monday_Briefing.md`

### 11.4 Report Sections

```
1. Executive Summary (one paragraph)
2. Revenue (this week, MTD, % of target, trend)
3. Completed Tasks (checklist from /Tasks/Done/)
4. Bottlenecks (tasks that took 2x longer than expected)
5. Social Media Summary (posts, impressions, engagements per platform)
6. Subscription Audit (flag unused or cost-increased tools)
7. Proactive Suggestions (written to /Pending_Approval/)
8. AI Actions Summary (emails sent, invoices, posts, approvals)
```

### 11.5 Subscription Audit Rules

Flag for review if:
- No usage in last 30 days
- Cost increased more than 20%
- Duplicate functionality with another tool
- Total software spend exceeds $500/month

---

## 12. Error Recovery

### 12.1 Error Categories

| Category | Examples | Recovery |
|----------|---------|---------|
| Transient | Network timeout, rate limit | Exponential backoff retry |
| Auth | Expired token, revoked access | Alert human, pause operations |
| Logic | Claude misinterprets message | Human review queue |
| Data | Corrupted file, missing field | Quarantine + alert |
| System | Orchestrator crash, disk full | Watchdog + auto-restart |

### 12.2 Retry Logic

```
Attempt 1 → wait 1 second
Attempt 2 → wait 2 seconds
Attempt 3 → wait 4 seconds
Max delay : 60 seconds
Max attempts : 3
```

### 12.3 Special Rules

- Gmail API down → queue emails locally, process when restored
- Banking API timeout → NEVER retry automatically, require fresh human approval
- Claude Code unavailable → watchers keep collecting, queue grows
- Obsidian vault locked → write to /tmp/, sync when available

### 12.4 Circuit Breaker States

```
CLOSED   → Normal, requests flow through
OPEN     → Service failing, all requests blocked
HALF     → 1 trial request to test recovery
```

- Trip after: 5 consecutive failures
- Cooldown: 60 seconds
- On trip: write to Dashboard.md + /Needs_Action/

### 12.5 Health Monitor

Check intervals:

| Check | Interval |
|-------|---------|
| Process alive | Every 60 seconds |
| Disk space | Every 10 minutes |
| API token validity | Every 6 hours |
| Full system report | Every 1 hour |

Auto-heal actions:
- Process crashed → restart via PM2 + alert human
- Disk full → archive old /Done/ files + alert
- Token expired → pause that service + alert human

---

## 13. Orchestrator

### 13.1 Responsibilities

- Folder watching (/Needs_Action/, /Approved/)
- Scheduling (cron jobs)
- Process management (start/stop watchers)
- Triggering Claude Code with correct skill
- Moving files between folders
- Calling MCP actions after approval

### 13.2 Scheduled Tasks

| Task | Schedule | Skill |
|------|---------|-------|
| Weekly CEO Briefing | Sunday 11:00 PM | weekly-audit-generator |
| Health Check Report | Every hour | health-monitor |
| Social Media Check | Every 30 minutes | social-listener |
| Finance Watch | Every 15 minutes | payment-tracker |

---

## 14. Security

### 14.1 Credential Storage

```env
# .env — NEVER commit this file, add to .gitignore

# Gmail
GMAIL_CLIENT_ID=
GMAIL_CLIENT_SECRET=

# Meta (Facebook + Instagram)
FACEBOOK_PAGE_ID=
FACEBOOK_ACCESS_TOKEN=
INSTAGRAM_ACCOUNT_ID=

# X / Twitter
X_API_KEY=
X_API_SECRET=
X_ACCESS_TOKEN=
X_ACCESS_SECRET=
X_BEARER_TOKEN=

# Odoo
ODOO_URL=http://localhost:8069
ODOO_DB=
ODOO_USERNAME=
ODOO_PASSWORD=

# Social Listener
BRAND_KEYWORDS=YourBrand,@YourHandle,#YourHashtag
MENTION_CHECK_INTERVAL=1800

# Safety
DRY_RUN=true
MAX_AUTO_PAYMENT=50
MAX_RETRY_ATTEMPTS=3
BASE_RETRY_DELAY=1
MAX_RETRY_DELAY=60
PAYMENT_RETRY=false
FAILURE_THRESHOLD=5
COOLDOWN_SECONDS=60
DISK_ALERT_THRESHOLD_GB=1
```

### 14.2 Rules

- Never store credentials in Obsidian vault
- Never commit .env to Git
- DRY_RUN=true during development
- Rotate credentials monthly
- All scripts support --dry-run flag

### 14.3 Audit Log Format

```json
{
  "timestamp": "2026-01-07T10:30:00Z",
  "action_type": "email_send",
  "actor": "claude_code",
  "target": "client@example.com",
  "parameters": {"subject": "Invoice #123"},
  "approval_status": "approved",
  "approved_by": "human",
  "result": "success"
}
```

Store at: `/Logs/YYYY-MM-DD.json`  
Retention: minimum 90 days

---

## 15. End-to-End Example Flow (Invoice)

```
1. Client sends WhatsApp: "send me the invoice for January"
        ↓
2. whatsapp_watcher.py detects keyword "invoice"
   Writes: /Needs_Action/WHATSAPP_client_a_<date>.md
        ↓
3. Orchestrator triggers Claude Code + invoice-processor skill
        ↓
4. Claude reads:
   - /Clients/Client_A.md  (contact info)
   - /Accounting/Rates.md  (pricing)
        ↓
5. Claude creates draft invoice in Odoo
   Writes: /Plans/PLAN_invoice_client_a.md
   Writes: /Pending_Approval/INVOICE_client_a_<date>.md
        ↓
6. Human reviews and moves file to /Approved/
        ↓
7. Orchestrator detects /Approved/ file
   Calls email-mcp → sends invoice
   Posts invoice in Odoo
        ↓
8. Files moved to /Done/
   Log written to /Logs/YYYY-MM-DD.json
   Dashboard.md updated
```

---

## 16. Gold Tier Checklist

### Core Requirements
- [ ] All Silver Tier requirements complete
- [ ] Full cross-domain integration (Personal + Business)
- [ ] Ralph Wiggum loop implemented (Stop hook)
- [ ] All 14 skills created in .claude/skills/

### Social Media
- [ ] LinkedIn — post + engagement summary
- [ ] Facebook — post + comment monitoring
- [ ] Instagram — post + hashtags + metrics
- [ ] Twitter/X — tweet + thread + mention monitoring
- [ ] Social Listener — cross-platform brand monitoring

### Accounting
- [ ] Odoo Community installed and running locally
- [ ] odoo-accounting-mcp skill connected via JSON-RPC
- [ ] invoice-processor skill working (draft + approve flow)
- [ ] payment-tracker skill reconciling transactions
- [ ] financial-reporting skill generating summaries

### CEO Briefing
- [ ] weekly-audit-generator running via cron Sunday 11 PM
- [ ] Report includes revenue, bottlenecks, subscriptions, suggestions
- [ ] Proactive suggestions written to /Pending_Approval/
- [ ] Dashboard.md updated after each briefing

### Error Recovery
- [ ] error-recovery-manager with exponential backoff
- [ ] circuit-breaker per service (5 failure threshold)
- [ ] health-monitor restarting crashed processes via PM2
- [ ] All watchers managed by PM2

### Security
- [ ] .env file created and added to .gitignore
- [ ] DRY_RUN=true confirmed during development
- [ ] Audit logs writing to /Logs/ with 90-day retention
- [ ] HITL active for all payments > $100 and new payees

### Documentation
- [ ] README.md with setup instructions
- [ ] Architecture overview written
- [ ] Demo video recorded (5–10 minutes)
- [ ] Security disclosure documented
- [ ] Tier declared as Gold in submission form

---

## 17. Submission

- GitHub repository (public or with judge access)
- README.md with setup + architecture
- Demo video: 5–10 minutes showing key features
- Security disclosure: how credentials are handled
- Tier declaration: Gold


---

*Spec based on: Personal AI Employee Hackathon 0 — Building Autonomous FTEs in 2026*