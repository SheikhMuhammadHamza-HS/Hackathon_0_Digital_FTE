---
name: ceo-briefing
description: Generate weekly CEO briefings with financial summaries, revenue tracking, task analysis, and proactive suggestions. Depends on odoo-accounting-mcp and payment-tracker skills. Runs automatically every Sunday at 11pm. Use when Claude needs to: (1) Generate weekly financial summaries, (2) Track progress against business goals, (3) Analyze task completion and bottlenecks, (4) Audit subscriptions and expenses, (5) Create proactive business recommendations
license: Complete terms in LICENSE.txt
---

# CEO Briefing

This skill generates comprehensive weekly CEO briefings with financial analysis, performance metrics, and strategic insights for executive decision-making.

## Dependencies

This skill requires:
- `odoo-accounting-mcp` skill for invoice/payment data
- `payment-tracker` skill for transaction analytics
- Business_Goals.md for target metrics
- Access to /Tasks/Done for completion analysis
- Bank_Transactions.md for cash flow data

## Quick Start

Generate weekly briefing:
```bash
/ceo-briefing-generate --week 2024-W03

Generate custom briefing:
```bash
/ceo-briefing-generate --date 2024-01-21 --custom-targets
```

Check briefing schedule:
```bash
/ceo-briefing-schedule
```

## Automated Schedule

**Cron Configuration:**
```bash
0 23 * * 0  # Every Sunday at 11:00 PM
```

**Automation Process:**
1. Sunday 11:00 PM - Trigger automatically
2. Pull all weekly data
3. Generate comprehensive briefing
4. Save to /Briefings/YYYY-MM-DD_Monday_Briefing.md
5. Create proactive suggestions in /Pending_Approval/

## Core Components

### 1. Business Goals Integration

**Business_Goals.md Structure:**
```markdown
---
year: 2024
last_updated: 2024-01-21
---

# 2024 Business Goals

## Revenue Targets
- **January:** $50,000
- **Q1:** $150,000
- **2024:** $600,000

## KPI Targets
- **Monthly Recurring Revenue (MRR):** $40,000
- **Customer Acquisition Cost (CAC):** $500
- **Customer Lifetime Value (LTV):** $6,000
- **Gross Margin:** 70%

## Operational Goals
- **Task Completion Rate:** >90%
- **Average Task Duration:** <3 days
- **Client Satisfaction:** >4.5/5
```

### 2. Data Collection Sources

**Financial Data:**
- Odoo invoices (draft + posted)
- Odoo payments (reconciliation status)
- Bank transactions (cash flow)
- Subscription expenses (recurring)

**Operational Data:**
- /Tasks/Done (completed tasks)
- /Tasks/Failed (failed tasks)
- /Tasks/Inbox (pending tasks)
- /Vault/Logs/ (activity logs)

### 3. Briefing Structure

**Generated Briefing Format:**
```markdown
---
briefing_date: 2024-01-22
week_number: 2024-W03
period: 2024-01-15 to 2024-01-21
generated_by: claude
generated_at: 2024-01-21 23:00:00
---

# CEO Briefing - Week of January 15, 2024

## Executive Summary
📊 **Weekly Revenue:** $12,450 (124% of target)
📈 **MTD Revenue:** $38,750 (77.5% of January target)
✅ **Tasks Completed:** 24/27 (89% completion rate)
⚠️ **Bottlenecks:** 2 tasks exceeded SLA
💡 **Proactive Suggestions:** 3 items for review

---

## Financial Performance

### Revenue Analysis
| Metric | This Week | Target | Variance |
|--------|-----------|--------|----------|
| **Revenue** | $12,450 | $10,000 | +$2,450 |
| **Invoices Sent** | 8 | 7 | +1 |
| **Payments Received** | $10,800 | $9,000 | +$1,800 |
| **Outstanding** | $1,650 | - | - |

### Month-to-Date Progress
- **January Target:** $50,000
- **Current MTD:** $38,750 (77.5%)
- **Remaining Needed:** $11,250 (22.5%)
- **Daily Run Rate Needed:** $3,750

### Cash Flow Summary
- **Starting Balance:** $25,000
- **Inflows:** +$10,800
- **Outflows:** -$8,200
- **Ending Balance:** $27,600

---

## Operational Performance

### Task Completion
| Status | Count | Percentage |
|--------|-------|------------|
| **Completed** | 24 | 89% |
| **In Progress** | 2 | 7% |
| **Failed** | 1 | 4% |

### Bottleneck Analysis
**Tasks Exceeding SLA:**
1. **Invoice Processing** - Client X invoice took 5 days (SLA: 2 days)
   - Cause: Awaiting client approval
   - Impact: Delayed revenue recognition
   - Action: Implement automated reminders

2. **Bank Reconciliation** - Weekly reconciliation took 3 days (SLA: 1 day)
   - Cause: Banking API downtime
   - Impact: Delayed financial reporting
   - Action: Manual backup procedures implemented

---

## Subscription & Expense Audit

### Active Subscriptions
| Service | Cost | Usage | Status |
|---------|------|-------|---------|
| **Adobe Creative** | $59/mo | High | ✅ Keep |
| **Zoom Pro** | $149/mo | Medium | ✅ Keep |
| **Software Tool X** | $99/mo | Low | ⚠️ Review |
| **Analytics Suite** | $299/mo | None | ❌ Cancel |

**Recommendations:**
- **Cancel:** Software Tool X (unused for 60 days)
- **Downgrade:** Analytics Suite (no usage detected)
- **Savings:** $398/month

---

## Upcoming Deadlines

### This Week
- **Monday:** Q1 planning meeting
- **Wednesday:** Tax filing deadline
- **Friday:** Client deliverables due

### Next Week
- **Monday:** Board meeting preparation
- **Tuesday:** Performance reviews
- **Wednesday:** Contract renewals

---

## Proactive Suggestions

### High Priority Items
1. **Optimize Invoice Processing**
   - Implement automated approval reminders
   - Reduce processing time from 5 to 2 days
   - **Expected Impact:** +15% faster cash collection
   - **File:** /Pending_Approval/invoice-automation-improvement.md

2. **Cancel Unused Subscriptions**
   - Immediate savings of $398/month
   - Annual impact: $4,776
   - **File:** /Pending_Approval/subscription-cleanup-2024-W03.md

3. **Expand High-Value Service**
   - Consulting services showing 200% demand
   - Opportunity to add 2 more consultants
   - **File:** /Pending_Approval/team-expansion-proposal.md

### Strategic Insights
- **Client Retention:** 95% retention rate (industry avg: 85%)
- **Service Mix:** Consulting outperforming product sales 3:1
- **Market Opportunity:** AI integration requests increasing

---

## Risk Factors & Mitigation

### Current Risks
1. **Dependency Risk:** 40% revenue from top 3 clients
   - Mitigation: Diversification strategy in progress

2. **Cash Flow Gap:** Large payment due in 2 weeks
   - Mitigation: Accelerate invoicing for new projects

3. **Resource Constraint:** Team at 85% capacity
   - Mitigation: Freelancer pipeline established

---

## Next Week Focus
1. Close $11,250 needed for January target
2. Implement subscription cost savings
3. Address invoice processing bottlenecks
4. Prepare for Q1 planning meeting

---
*Generated by Claude on 2024-01-21 23:00:00*
*Next briefing: 2024-01-28 23:00:00*
```

## Implementation Details

### Data Collection Functions
```python
def collect_weekly_data():
    """Gather all data for weekly briefing"""

    # Financial data from Odoo
    weekly_invoices = get_odoo_invoices(week_start, week_end)
    weekly_payments = get_odoo_payments(week_start, week_end)

    # Bank transactions
    bank_data = parse_bank_transactions(week_start, week_end)

    # Task data
    completed_tasks = get_tasks_done(week_start, week_end)
    failed_tasks = get_tasks_failed(week_start, week_end)

    # Business goals
    targets = load_business_goals()

    return {
        'financial': process_financial_data(weekly_invoices, weekly_payments, bank_data),
        'operational': process_task_data(completed_tasks, failed_tasks),
        'targets': targets
    }
```

### Revenue Analysis Logic
```python
def analyze_revenue_performance(invoices, payments, targets):
    weekly_revenue = sum(inv.amount for inv in invoices if inv.state == 'posted')
    weekly_target = targets['weekly_revenue']

    # MTD calculations
    mtd_start = datetime.now().replace(day=1)
    mtd_invoices = get_odoo_invoices(mtd_start, datetime.now())
    mtd_revenue = sum(inv.amount for inv in mtd_invoices if inv.state == 'posted')
    mtd_target = targets['monthly_revenue']

    return {
        'weekly': {
            'actual': weekly_revenue,
            'target': weekly_target,
            'variance': weekly_revenue - weekly_target,
            'variance_pct': ((weekly_revenue - weekly_target) / weekly_target) * 100
        },
        'mtd': {
            'actual': mtd_revenue,
            'target': mtd_target,
            'remaining': mtd_target - mtd_revenue,
            'completion_pct': (mtd_revenue / mtd_target) * 100
        }
    }
```

### Bottleneck Detection
```python
def detect_bottlenecks(completed_tasks, failed_tasks):
    bottlenecks = []
    sla_threshold = timedelta(days=3)  # From Business_Goals.md

    for task in completed_tasks:
        duration = task.completed_at - task.started_at
        if duration > sla_threshold:
            bottlenecks.append({
                'task': task.name,
                'duration': duration,
                'sla': sla_threshold,
                'excess': duration - sla_threshold,
                'impact': assess_impact(task),
                'suggestion': generate_suggestion(task)
            })

    return bottlenecks
```

### Subscription Audit
```python
def audit_subscriptions():
    subscriptions = load_subscription_data()
    audit_results = []

    for sub in subscriptions:
        usage = calculate_usage(sub.service, period=30)
        efficiency = usage / sub.cost

        status = "keep"
        if efficiency < 0.1:
            status = "cancel"
        elif efficiency < 0.5:
            status = "review"

        audit_results.append({
            'service': sub.service,
            'cost': sub.cost,
            'usage': usage,
            'efficiency': efficiency,
            'status': status,
            'savings': sub.cost if status == "cancel" else 0
        })

    return audit_results
```

## Commands Reference

### Generation Commands
```bash
# Generate current week briefing
/ceo-briefing-generate

# Generate specific week
/ceo-briefing-generate --week 2024-W03

# Generate custom date range
/ceo-briefing-generate --start 2024-01-01 --end 2024-01-07

# Preview briefing without saving
/ceo-briefing-preview --week 2024-W03
```

### Configuration Commands
```bash
# Set cron schedule
/ceo-briefing-schedule --cron "0 23 * * 0"

# Test cron configuration
/ceo-briefing-schedule --test

# Disable automation
/ceo-briefing-schedule --disable

# Check next run time
/ceo-briefing-schedule --next
```

### Analysis Commands
```bash
# Analyze revenue trends
/ceo-briefing-analyze --metric revenue --period 4w

# Compare weeks
/ceo-briefing-compare --week 2024-W03 --vs 2024-W02

# Deep dive on specific metric
/ceo-briefing-deepdive --metric tasks --week 2024-W03
```

## Proactive Suggestions Generation

### Suggestion Categories
1. **Revenue Optimization**
   - Pricing adjustments
   - Service expansion
   - Client retention

2. **Cost Reduction**
   - Subscription cleanup
   - Process automation
   - Resource optimization

3. **Risk Mitigation**
   - Diversification
   - Cash flow management
   - Dependency reduction

### Suggestion File Format
**Location:** `/Pending_Approval/suggestion-YYYY-MM-DD.md`

```markdown
---
type: proactive_suggestion
category: cost_reduction
priority: high
estimated_impact: 4776
timeframe: 1_month
generated_by: ceo-briefing
date: 2024-01-21
---

# Cancel Unused Subscriptions - $398/month Savings

## Summary
Audit identified 2 subscriptions with minimal usage that can be cancelled immediately.

## Details
- **Software Tool X:** $99/month (0% usage)
- **Analytics Suite:** $299/month (5% usage)

## Action Required
[ ] Cancel Software Tool X subscription
[ ] Downgrade Analytics Suite to basic plan
[ ] Update budget forecasts

## Expected Impact
- **Monthly Savings:** $398
- **Annual Impact:** $4,776
- **Implementation Time:** 1 week

---
*Generated by CEO Briefing - Week 2024-W03*
```

## Automation Setup

### Cron Job Configuration
```bash
# Add to crontab
crontab -e

# Add line:
0 23 * * 0 cd /d/hackathon_zero && /usr/bin/python3 -c "from claude_skills import ceo_briefing; ceo_briefing.generate_weekly_briefing()"

# Verify installation
crontab -l
```

### Python Automation Script
```python
#!/usr/bin/env python3
"""CEO Briefing Automation Script"""

import schedule
import time
from datetime import datetime

def run_weekly_briefing():
    """Run weekly briefing generation"""
    try:
        briefing_skill = get_skill('ceo-briefing')
        briefing_skill.generate_weekly_briefing()
        log_success("Weekly briefing generated successfully")
    except Exception as e:
        log_error(f"Failed to generate briefing: {str(e)}")

# Schedule
schedule.every().sunday.at("23:00").do(run_weekly_briefing)

# Keep running
while True:
    schedule.run_pending()
    time.sleep(60)
```

## Error Handling

### Data Availability Issues
```python
def handle_missing_data():
    """Handle cases where data sources are unavailable"""

    # Odoo connection issues
    if not odoo_is_available():
        use_cached_financial_data()
        add_warning("Using cached financial data - Odoo unavailable")

    # Missing business goals
    if not business_goals_exist():
        use_default_targets()
        add_warning("Using default targets - Business_Goals.md not found")

    # Task data issues
    if task_data_incomplete():
        estimate_missing_tasks()
        add_warning("Task data incomplete - using estimates")
```

### Validation Checks
```python
def validate_briefing_data(data):
    """Ensure data integrity before generating briefing"""

    errors = []

    # Financial validation
    if data['financial']['revenue'] < 0:
        errors.append("Negative revenue detected")

    # Task validation
    if data['operational']['completion_rate'] > 100:
        errors.append("Task completion rate exceeds 100%")

    # Consistency checks
    if not data_consistent(data):
        errors.append("Data inconsistencies detected")

    if errors:
        raise ValidationError(f"Data validation failed: {errors}")
```

## Performance Optimization

### Data Caching
- Cache Odoo queries for 24 hours
- Cache business goals until updated
- Cache task completion metrics
- Cache subscription audit results

### Batch Processing
- Collect all data first
- Process in memory
- Generate briefing in one pass
- Save all suggestions at once

## Best Practices

1. **Data Accuracy**: Always validate data before reporting
2. **Consistency**: Use same metrics week to week
3. **Actionability**: Make suggestions specific and measurable
4. **Timeliness**: Generate at consistent time
5. **Backup**: Keep historical briefings for trend analysis
6. **Review**: Monthly review of briefing effectiveness

## Troubleshooting

### Common Issues
1. **"Briefing generation failed"**
   - Check Odoo connectivity
   - Verify Business_Goals.md exists
   - Review file permissions

2. **"Missing financial data"**
   - Check Odoo date range queries
   - Verify invoice posting status
   - Review currency settings

3. **"Task data incomplete"**
   - Check /Tasks/Done directory
   - Verify task file format
   - Review task completion dates

4. **"Cron job not running"**
   - Check cron service status
   - Verify cron syntax
   - Review script permissions

## Security Considerations

1. **Data Privacy**: Limit sensitive financial data
2. **Access Control**: Restrict briefing access
3. **Audit Trail**: Log all briefing generations
4. **Data Retention**: Define retention policy
5. **Encryption**: Secure sensitive metrics