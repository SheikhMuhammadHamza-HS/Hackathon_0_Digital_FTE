---
name: business-handover
description: Compile complete business and accounting weekly summary for CEO briefing. Integrates Odoo data, bank transactions, task completion, social media metrics, and subscription audits. Generates comprehensive Monday Morning CEO Briefing with proactive suggestions. Depends on odoo-accounting-mcp, financial-reporting, payment-tracker, and social-listener skills.
license: Complete terms in LICENSE.txt
---

# Business Handover

This skill compiles comprehensive weekly business summaries for CEO briefings, integrating financial data, operational metrics, and strategic insights as specified in hackathon guide Section 4.

## Dependencies

This skill requires:
- `odoo-accounting-mcp` skill for invoice/payment data
- `financial-reporting` skill for financial analysis
- `payment-tracker` skill for transaction analytics
- `social-listener` skill for engagement metrics

## Triggers

### Automated Trigger
- **Cron Schedule**: Every Sunday at 11:00 PM
- **Command**: `0 23 * * 0 cd /d/hackathon_zero && business-handover-generate`

### Manual Trigger
- **File Trigger**: Drop `AUDIT_REQUEST.md` into `/Needs_Action/`
- **Command**: `/business-handover-generate`

## Data Sources Integration

### Primary Data Sources
| Source | Data Collected | Integration Method |
|--------|----------------|-------------------|
| Business_Goals.md | Targets, KPIs, thresholds | Direct file read |
| Odoo JSON-RPC | Invoices, payments, balances | API integration |
| Bank_Transactions.md | All bank activity this week | File parsing |
| /Tasks/Done/ | Completed tasks + time taken | Directory scan |
| /Logs/ | AI actions taken this week | Log analysis |
| social-listener | Mentions, engagement metrics | Skill integration |

## Core Implementation

### Business Handover Engine

```python
import os
import json
import yaml
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class WeeklyMetrics:
    week_number: str
    period_start: datetime
    period_end: datetime
    revenue: Dict[str, float]
    expenses: Dict[str, float]
    tasks_completed: int
    social_metrics: Dict[str, Any]
    subscription_audit: List[Dict[str, Any]]
    bottlenecks: List[Dict[str, Any]]
    suggestions: List[Dict[str, Any]]

class BusinessHandoverEngine:
    def __init__(self):
        self.data_collectors = {
            'business_goals': self._collect_business_goals,
            'odoo_data': self._collect_odoo_data,
            'bank_transactions': self._collect_bank_transactions,
            'task_completion': self._collect_task_data,
            'ai_actions': self._collect_ai_actions,
            'social_metrics': self._collect_social_metrics,
            'subscriptions': self._audit_subscriptions
        }

    def generate_weekly_briefing(self, target_date: Optional[datetime] = None) -> str:
        """Generate comprehensive weekly CEO briefing"""

        if target_date is None:
            target_date = datetime.now()

        # Determine week period
        week_start = target_date - timedelta(days=target_date.weekday())
        week_end = week_start + timedelta(days=6)
        week_number = target_date.strftime('%Y-W%U')

        # Collect all data
        briefing_data = {
            'metadata': {
                'week_number': week_number,
                'period_start': week_start.strftime('%Y-%m-%d'),
                'period_end': week_end.strftime('%Y-%m-%d'),
                'generated_at': target_date.isoformat(),
                'generated_by': 'business-handover'
            },
            'business_goals': self._collect_business_goals(),
            'financial_data': self._collect_financial_data(week_start, week_end),
            'operational_data': self._collect_operational_data(week_start, week_end),
            'social_data': self._collect_social_data(week_start, week_end),
            'subscription_audit': self._audit_subscriptions(),
            'bottlenecks': self._detect_bottlenecks(week_start, week_end),
            'suggestions': self._generate_suggestions()
        }

        # Generate briefing content
        briefing_content = self._format_briefing(briefing_data)

        # Save briefing
        briefing_file = f"/Briefings/{target_date.strftime('%Y-%m-%d')}_Monday_Briefing.md"
        self._save_briefing(briefing_file, briefing_content)

        # Create proactive suggestions
        self._create_suggestion_files(briefing_data['suggestions'])

        # Update dashboard
        self._update_dashboard(briefing_data)

        return briefing_file

    def _collect_business_goals(self) -> Dict[str, Any]:
        """Read business goals and targets"""

        try:
            with open('Business_Goals.md', 'r') as f:
                content = f.read()

            # Parse YAML frontmatter
            if content.startswith('---'):
                _, frontmatter, body = content.split('---', 2)
                goals = yaml.safe_load(frontmatter)
            else:
                goals = {}

            # Extract specific targets
            return {
                'revenue_targets': goals.get('revenue_targets', {}),
                'kpi_targets': goals.get('kpi_targets', {}),
                'operational_goals': goals.get('operational_goals', {}),
                'thresholds': goals.get('thresholds', {})
            }

        except Exception as e:
            log_error(f"Failed to read Business_Goals.md: {str(e)}")
            return {}

    def _collect_financial_data(self, week_start: datetime, week_end: datetime) -> Dict[str, Any]:
        """Collect financial data from Odoo and bank transactions"""

        financial_data = {
            'odoo_invoices': [],
            'odoo_payments': [],
            'bank_transactions': [],
            'revenue_summary': {},
            'expense_summary': {},
            'cash_flow': {}
        }

        # Collect Odoo data
        try:
            # Get odoo-accounting-mcp skill
            odoo_skill = get_skill('odoo-accounting-mcp')

            # Get invoices for the week
            invoices = odoo_skill.get_weekly_invoices(week_start, week_end)
            financial_data['odoo_invoices'] = invoices

            # Get payments for the week
            payments = odoo_skill.get_weekly_payments(week_start, week_end)
            financial_data['odoo_payments'] = payments

            # Calculate revenue summary
            total_invoiced = sum(inv['amount'] for inv in invoices)
            total_paid = sum(pay['amount'] for pay in payments)
            outstanding = total_invoiced - total_paid

            financial_data['revenue_summary'] = {
                'total_invoiced': total_invoiced,
                'total_paid': total_paid,
                'outstanding': outstanding,
                'payment_rate': (total_paid / total_invoiced * 100) if total_invoiced > 0 else 0
            }

        except Exception as e:
            log_error(f"Failed to collect Odoo data: {str(e)}")

        # Collect bank transactions
        try:
            with open('Bank_Transactions.md', 'r') as f:
                bank_content = f.read()

            # Parse transactions for the week
            financial_data['bank_transactions'] = self._parse_bank_transactions(
                bank_content, week_start, week_end
            )

            # Calculate cash flow
            inflows = sum(t['amount'] for t in financial_data['bank_transactions'] if t['amount'] > 0)
            outflows = abs(sum(t['amount'] for t in financial_data['bank_transactions'] if t['amount'] < 0))

            financial_data['cash_flow'] = {
                'inflows': inflows,
                'outflows': outflows,
                'net_flow': inflows - outflows
            }

        except Exception as e:
            log_error(f"Failed to collect bank transactions: {str(e)}")

        return financial_data

    def _collect_operational_data(self, week_start: datetime, week_end: datetime) -> Dict[str, Any]:
        """Collect operational data from tasks and logs"""

        operational_data = {
            'tasks_completed': [],
            'task_metrics': {},
            'ai_actions': [],
            'efficiency_metrics': {}
        }

        # Collect completed tasks
        try:
            tasks_done_dir = Path('/Tasks/Done')
            if tasks_done_dir.exists():
                for task_file in tasks_done_dir.glob('*.md'):
                    # Check if task was completed this week
                    file_time = datetime.fromtimestamp(task_file.stat().st_mtime)
                    if week_start <= file_time <= week_end:
                        task_data = self._parse_task_file(task_file)
                        operational_data['tasks_completed'].append(task_data)

            # Calculate task metrics
            total_tasks = len(operational_data['tasks_completed'])
            if total_tasks > 0:
                # Calculate average completion time
                completion_times = [
                    task.get('completion_time_hours', 0)
                    for task in operational_data['tasks_completed']
                ]
                avg_completion = sum(completion_times) / len(completion_times)

                operational_data['task_metrics'] = {
                    'total_completed': total_tasks,
                    'avg_completion_hours': avg_completion,
                    'on_time_rate': self._calculate_on_time_rate(operational_data['tasks_completed'])
                }

        except Exception as e:
            log_error(f"Failed to collect task data: {str(e)}")

        # Collect AI actions from logs
        try:
            log_files = list(Path('/Logs').glob(f'{week_start.strftime("%Y-%m-%d")}*.json'))
            ai_actions = []

            for log_file in log_files:
                with open(log_file, 'r') as f:
                    logs = json.load(f)
                    for log_entry in logs:
                        if 'operation' in log_entry:
                            ai_actions.append(log_entry)

            operational_data['ai_actions'] = ai_actions
            operational_data['efficiency_metrics'] = self._calculate_efficiency_metrics(ai_actions)

        except Exception as e:
            log_error(f"Failed to collect AI actions: {str(e)}")

        return operational_data

    def _collect_social_data(self, week_start: datetime, week_end: datetime) -> Dict[str, Any]:
        """Collect social media metrics and engagement data"""

        try:
            # Get social-listener skill
            social_skill = get_skill('social-listener')

            # Get weekly metrics
            social_metrics = social_skill.get_weekly_metrics(week_start, week_end)

            return social_metrics

        except Exception as e:
            log_error(f"Failed to collect social data: {str(e)}")
            return {}

    def _audit_subscriptions(self) -> List[Dict[str, Any]]:
        """Audit all active subscriptions and flag issues"""

        subscription_audit = []

        try:
            # Read subscription data
            subscriptions = self._load_subscription_data()

            for subscription in subscriptions:
                audit_result = self._audit_single_subscription(subscription)
                subscription_audit.append(audit_result)

        except Exception as e:
            log_error(f"Failed to audit subscriptions: {str(e)}")

        return subscription_audit

    def _audit_single_subscription(self, subscription: Dict[str, Any]) -> Dict[str, Any]:
        """Audit a single subscription according to hackathon rules"""

        audit_result = {
            'name': subscription.get('name', 'Unknown'),
            'cost': subscription.get('cost', 0),
            'last_usage': subscription.get('last_usage'),
            'usage_days_ago': 0,
            'flags': [],
            'recommendation': 'keep'
        }

        # Rule 1: No login/usage in last 30 days
        if subscription.get('last_usage'):
            last_usage = datetime.fromisoformat(subscription['last_usage'])
            days_since_use = (datetime.now() - last_usage).days
            audit_result['usage_days_ago'] = days_since_use

            if days_since_use > 30:
                audit_result['flags'].append('No usage in 30 days')
                audit_result['recommendation'] = 'review'

        # Rule 2: Cost increased more than 20%
        if subscription.get('previous_cost'):
            cost_increase = (subscription['cost'] - subscription['previous_cost']) / subscription['previous_cost']
            if cost_increase > 0.20:
                audit_result['flags'].append(f'Cost increase {cost_increase*100:.1f}%')
                audit_result['recommendation'] = 'review'

        # Rule 3: Duplicate functionality
        if subscription.get('duplicate_of'):
            audit_result['flags'].append(f'Duplicate of {subscription["duplicate_of"]}')
            audit_result['recommendation'] = 'consolidate'

        # Rule 4: Total software spend > $500/month
        monthly_spend = sum(s.get('cost', 0) for s in self._load_subscription_data())
        if monthly_spend > 500:
            audit_result['flags'].append(f'Total spend ${monthly_spend:.0f} exceeds $500 threshold')
            if subscription['cost'] > 100:  # Flag expensive ones
                audit_result['recommendation'] = 'review'

        return audit_result

    def _detect_bottlenecks(self, week_start: datetime, week_end: datetime) -> List[Dict[str, Any]]:
        """Detect operational bottlenecks from task data"""

        bottlenecks = []

        try:
            # Get completed tasks for the week
            tasks_done_dir = Path('/Tasks/Done')
            if not tasks_done_dir.exists():
                return bottlenecks

            for task_file in tasks_done_dir.glob('*.md'):
                file_time = datetime.fromtimestamp(task_file.stat().st_mtime)
                if week_start <= file_time <= week_end:
                    task_data = self._parse_task_file(task_file)

                    # Check if task took 2x longer than expected
                    expected_time = task_data.get('expected_time_hours', 0)
                    actual_time = task_data.get('completion_time_hours', 0)

                    if expected_time > 0 and actual_time > (expected_time * 2):
                        bottleneck = {
                            'task_name': task_data.get('name', 'Unknown'),
                            'expected_time': expected_time,
                            'actual_time': actual_time,
                            'overrun_factor': actual_time / expected_time,
                            'impact': self._assess_task_impact(task_data),
                            'suggested_action': self._suggest_bottleneck_solution(task_data)
                        }
                        bottlenecks.append(bottleneck)

        except Exception as e:
            log_error(f"Failed to detect bottlenecks: {str(e)}")

        return bottlenecks

    def _generate_suggestions(self) -> List[Dict[str, Any]]:
        """Generate proactive business suggestions"""

        suggestions = []

        # Analyze all collected data and generate suggestions
        # This would integrate with the data collected above

        return suggestions

    def _format_briefing(self, briefing_data: Dict[str, Any]) -> str:
        """Format the complete CEO briefing"""

        metadata = briefing_data['metadata']
        goals = briefing_data['business_goals']
        financial = briefing_data['financial_data']
        operational = briefing_data['operational_data']
        social = briefing_data['social_data']
        subscriptions = briefing_data['subscription_audit']
        bottlenecks = briefing_data['bottlenecks']
        suggestions = briefing_data['suggestions']

        # Format executive summary
        executive_summary = self._format_executive_summary(
            financial, operational, social, goals
        )

        # Format financial performance
        financial_section = self._format_financial_section(financial, goals)

        # Format operational performance
        operational_section = self._format_operational_section(operational, bottlenecks)

        # Format subscription audit
        subscription_section = self._format_subscription_audit(subscriptions)

        # Format proactive suggestions
        suggestions_section = self._format_suggestions(suggestions)

        # Combine all sections
        briefing_content = f"""---
week: {metadata['week_number']}
period: {metadata['period_start']} to {metadata['period_end']}
generated_by: {metadata['generated_by']}
generated_at: {metadata['generated_at']}
---

# Monday Morning CEO Briefing - Week of {metadata['period_start']}

{executive_summary}

{financial_section}

{operational_section}

## Social Media & Brand Performance

{self._format_social_metrics(social)}

{subscription_section}

{suggestions_section}

## Risk Factors & Mitigation

{self._format_risk_factors(briefing_data)}

## Next Week Focus

{self._format_next_week_focus(briefing_data)}

---
*Generated by Business Handover Engine*
*Next briefing: {(datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')}*
"""

        return briefing_content

    def _format_executive_summary(self, financial: Dict, operational: Dict, social: Dict, goals: Dict) -> str:
        """Format executive summary section"""

        revenue = financial.get('revenue_summary', {})
        revenue_target = goals.get('revenue_targets', {}).get('weekly', 0)
        revenue_actual = revenue.get('total_invoiced', 0)
        revenue_variance = revenue_actual - revenue_target
        revenue_pct = (revenue_actual / revenue_target * 100) if revenue_target > 0 else 0

        tasks = operational.get('task_metrics', {})
        task_completion = tasks.get('total_completed', 0)
        on_time_rate = tasks.get('on_time_rate', 0)

        return f"""## Executive Summary

📊 **Weekly Revenue:** ${revenue_actual:,.2f} ({revenue_pct:.1f}% of target)
{'📈' if revenue_variance >= 0 else '📉'} **Variance:** ${revenue_variance:,.2f}
✅ **Tasks Completed:** {task_completion} ({on_time_rate:.1f}% on-time)
👥 **Social Engagement:** {social.get('total_engagements', 0)} interactions
⚠️ **Action Items:** {len([s for s in financial.get('subscriptions', []) if s.get('recommendation') == 'review'])} subscriptions to review

---

## Key Highlights
- **Top Performance:** {self._get_top_performer(financial, operational, social)}
- **Critical Issue:** {self._get_critical_issue(financial, operational, social)}
- **Opportunity:** {self._get_top_opportunity(financial, operational, social)}
"""

    def _format_financial_section(self, financial: Dict, goals: Dict) -> str:
        """Format financial performance section"""

        revenue = financial.get('revenue_summary', {})
        cash_flow = financial.get('cash_flow', {})

        return f"""## Financial Performance

### Revenue Analysis
| Metric | This Week | Target | Variance |
|--------|-----------|--------|----------|
| **Invoices Sent** | ${financial.get('total_invoiced', 0):,.2f} | ${goals.get('revenue_targets', {}).get('weekly', 0):,.2f} | ${revenue.get('total_invoiced', 0) - goals.get('revenue_targets', {}).get('weekly', 0):,.2f} |
| **Payments Received** | ${revenue.get('total_paid', 0):,.2f} | - | - |
| **Outstanding** | ${revenue.get('outstanding', 0):,.2f} | - | - |
| **Payment Rate** | {revenue.get('payment_rate', 0):,.1f}% | 95% | {revenue.get('payment_rate', 0) - 95:.1f}% |

### Cash Flow Summary
- **Inflows:** +${cash_flow.get('inflows', 0):,.2f}
- **Outflows:** -${cash_flow.get('outflows', 0):,.2f}
- **Net Flow:** {cash_flow.get('net_flow', 0):+,.2f}

### Top Invoices This Week
{self._format_top_invoices(financial.get('odoo_invoices', []))}
"""

    def _format_operational_section(self, operational: Dict, bottlenecks: List[Dict]) -> str:
        """Format operational performance section"""

        tasks = operational.get('task_metrics', {})
        ai_actions = operational.get('ai_actions', [])

        return f"""## Operational Performance

### Task Completion
- **Total Completed:** {tasks.get('total_completed', 0)}
- **Average Completion Time:** {tasks.get('avg_completion_hours', 0):.1f} hours
- **On-Time Rate:** {tasks.get('on_time_rate', 0):.1f}%

### AI Automation Summary
- **Actions Taken:** {len(ai_actions)}
- **Success Rate:** {self._calculate_ai_success_rate(ai_actions):.1f}%
- **Top Operations:** {self._get_top_ai_operations(ai_actions)}

### Bottleneck Analysis
{self._format_bottlenecks(bottlenecks)}
"""

    def _format_subscription_audit(self, subscriptions: List[Dict]) -> str:
        """Format subscription audit section"""

        flagged_subscriptions = [s for s in subscriptions if s.get('flags')]
        total_monthly_cost = sum(s.get('cost', 0) for s in subscriptions)
        flagged_cost = sum(s.get('cost', 0) for s in flagged_subscriptions)

        return f"""## Subscription Audit

### Overview
- **Total Subscriptions:** {len(subscriptions)}
- **Monthly Cost:** ${total_monthly_cost:.2f}
- **Flagged for Review:** {len(flagged_subscriptions)}
- **Potential Savings:** ${flagged_cost:.2f}

### Subscriptions Requiring Attention
{self._format_flagged_subscriptions(flagged_subscriptions)}

### Recommendations
{self._format_subscription_recommendations(flagged_subscriptions)}
"""

    def _create_suggestion_files(self, suggestions: List[Dict[str, Any]]):
        """Create individual suggestion files in /Pending_Approval/"""

        for suggestion in suggestions:
            suggestion_file = f"/Pending_Approval/{suggestion.get('category', 'general')}_{datetime.now().strftime('%Y-%m-%d')}.md"

            content = f"""---
type: proactive_suggestion
category: {suggestion.get('category', 'general')}
priority: {suggestion.get('priority', 'medium')}
estimated_impact: {suggestion.get('impact', 0)}
timeframe: {suggestion.get('timeframe', '1_month')}
generated_by: business-handover
date: {datetime.now().isoformat()}
---

# {suggestion.get('title', 'Business Suggestion')}

## Summary
{suggestion.get('summary', '')}

## Details
{suggestion.get('details', '')}

## Action Required
{suggestion.get('action_required', '')}

## Expected Impact
- **Financial:** ${suggestion.get('financial_impact', 0):,.2f}
- **Operational:** {suggestion.get('operational_impact', '')}
- **Timeframe:** {suggestion.get('timeframe', '1_month')}

---
*Generated by Business Handover - Week {datetime.now().strftime('%Y-W%U')}*
"""

            try:
                with open(suggestion_file, 'w') as f:
                    f.write(content)
                log_info(f"Created suggestion file: {suggestion_file}")
            except Exception as e:
                log_error(f"Failed to create suggestion file: {str(e)}")

    def _update_dashboard(self, briefing_data: Dict[str, Any]):
        """Update Dashboard.md with key metrics"""

        try:
            dashboard_file = "Dashboard.md"

            # Extract key metrics
            revenue = briefing_data['financial_data'].get('revenue_summary', {})
            tasks = briefing_data['operational_data'].get('task_metrics', {})
            social = briefing_data['social_data']

            # Create dashboard update
            dashboard_section = f"""## Business Metrics - This Week

- **Revenue:** ${revenue.get('total_invoiced', 0):,.2f}
- **Tasks Completed:** {tasks.get('total_completed', 0)}
- **On-Time Rate:** {tasks.get('on_time_rate', 0):.1f}%
- **Social Engagement:** {social.get('total_engagements', 0)}
- **Subscription Alerts:** {len([s for s in briefing_data['subscription_audit'] if s.get('flags')])}
"""

            # Update dashboard
            update_dashboard_section(dashboard_file, "Business Metrics", dashboard_section)

        except Exception as e:
            log_error(f"Failed to update dashboard: {str(e)}")
```

## Commands Reference

### Generation Commands
```bash
# Generate weekly briefing
/business-handover-generate

# Generate for specific week
/business-handover-generate --date 2024-01-15

# Preview briefing without saving
/business-handover-preview

# Generate from audit request
/business-handover-generate --trigger audit_request
```

### Data Collection Commands
```bash
# Collect financial data only
/business-handover-collect --data financial

# Collect operational data only
/business-handover-collect --data operational

# Test data sources
/business-handover-test-sources

# Validate business goals
/business-handover-validate-goals
```

### Analysis Commands
```bash
# Analyze revenue trends
/business-handover-analyze --metric revenue --period 4w

# Compare week over week
/business-handover-compare --week 2024-W03 --vs 2024-W02

# Subscription analysis
/business-handover-subscriptions --analyze

# Bottleneck analysis
/business-handover-bottlenecks --detail
```

### Report Commands
```bash
# Generate financial focus report
/business-handover-report --type financial

# Generate operational focus report
/business-handover-report --type operational

# Export briefing data
/business-handover-export --format json --week 2024-W03

# Archive old briefings
/business-handover-archive --older-than 90d
```

## Generated Output Format

### CEO Briefing Structure (`/Briefings/YYYY-MM-DD_Monday_Briefing.md`)

```markdown
---
week: 2024-W03
period: 2024-01-15 to 2024-01-21
generated_by: business-handover
generated_at: 2024-01-21T23:00:00Z
---

# Monday Morning CEO Briefing - Week of 2024-01-15

## Executive Summary

📊 **Weekly Revenue:** $15,750 (105% of target)
📈 **Variance:** +$750
✅ **Tasks Completed:** 24 (92% on-time)
👥 **Social Engagement:** 1,234 interactions
⚠️ **Action Items:** 3 subscriptions to review

## Financial Performance

### Revenue Analysis
| Metric | This Week | Target | Variance |
|--------|-----------|--------|----------|
| **Invoices Sent** | $15,750.00 | $15,000.00 | +$750.00 |
| **Payments Received** | $12,300.00 | - | - |
| **Outstanding** | $3,450.00 | - | - |
| **Payment Rate** | 78.1% | 95% | -16.9% |

## Operational Performance

### Task Completion
- **Total Completed:** 24
- **Average Completion Time:** 2.3 hours
- **On-Time Rate:** 92%

### Bottleneck Analysis
**Invoice Processing** - Took 6 hours (expected: 2 hours)
- **Impact:** Delayed revenue recognition
- **Suggestion:** Implement automated approval workflow

## Subscription Audit

### Subscriptions Requiring Attention
1. **Analytics Pro** - $299/month (No usage in 45 days)
2. **Design Suite** - $149/month (Duplicate functionality)
3. **Project Tool** - $99/month (Cost increased 25%)

**Potential Savings:** $547/month

## Proactive Suggestions

### High Priority
1. **Optimize Invoice Processing**
   - Implement automated reminders
   - Expected savings: 10 hours/week
   - File: /Pending_Approval/invoice-automation_2024-01-21.md

2. **Cancel Unused Subscriptions**
   - Immediate monthly savings: $547
   - File: /Pending_Approval/subscription-cleanup_2024-01-21.md

## Risk Factors & Mitigation

### Current Risks
1. **Payment Rate Below Target** - 78.1% vs 95% target
   - Mitigation: Implement payment follow-up automation

2. **Client Concentration** - 60% revenue from top 3 clients
   - Mitigation: Accelerate client diversification

## Next Week Focus
1. Improve payment collection rate to 90%
2. Cancel 2 unused subscriptions
3. Address invoice processing bottleneck
4. Follow up on outstanding invoices
```

## Integration with Other Skills

### Odoo Integration
```python
def get_odoo_financial_data(week_start, week_end):
    """Get financial data from odoo-accounting-mcp"""

    odoo_skill = get_skill('odoo-accounting-mcp')

    invoices = odoo_skill.get_invoices_by_date_range(week_start, week_end)
    payments = odoo_skill.get_payments_by_date_range(week_start, week_end)

    return {
        'invoices': invoices,
        'payments': payments,
        'revenue_summary': calculate_revenue_summary(invoices, payments)
    }
```

### Social Media Integration
```python
def get_social_metrics(week_start, week_end):
    """Get social media metrics from social-listener"""

    social_skill = get_skill('social-listener')

    return social_skill.get_weekly_engagement_report(week_start, week_end)
```

## Best Practices

1. **Data Validation**: Always validate data before inclusion
2. **Consistent Formatting**: Maintain consistent report structure
3. **Actionable Insights**: Ensure suggestions are specific and measurable
4. **Trend Analysis**: Include week-over-week comparisons
5. **Executive Focus**: Keep summaries concise and impactful

## Troubleshooting

### Common Issues
1. **"Failed to collect Odoo data"**
   - Check Odoo connection
   - Verify date ranges
   - Review API permissions

2. **"Business goals not found"**
   - Verify Business_Goals.md exists
   - Check YAML frontmatter format
   - Review target structure

3. **"Task data missing"**
   - Check /Tasks/Done directory
   - Verify task file format
   - Review date parsing logic

4. **"Suggestion files not created"**
   - Check /Pending_Approval/ permissions
   - Verify suggestion data structure
   - Review file creation logic

## Security Considerations

1. **Data Privacy**: Limit sensitive financial data in reports
2. **Access Control**: Restrict briefing access to authorized users
3. **Audit Trail**: Log all briefing generations
4. **Data Retention**: Define retention policy for briefings
5. **Secure Storage**: Encrypt sensitive business metrics