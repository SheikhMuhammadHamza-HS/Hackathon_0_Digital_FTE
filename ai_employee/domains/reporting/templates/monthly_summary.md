---
report_type: monthly_summary
month: {{ month_name }}
year: {{ year }}
period: {{ start_date }} to {{ end_date }}
generated_by: {{ generated_by }}
generated_at: {{ generated_at }}
---

# Monthly Summary - {{ month_name }} {{ year }}

## Executive Dashboard
📊 **Monthly Revenue:** ${{ financial.total_revenue | format_number }} ({{ financial.target_completion_pct | format_percent }} of target)
📈 **Growth vs Last Month:** {{ financial.month_over_month_growth | format_percent }}
✅ **Tasks Completed:** {{ operational.total_tasks_completed }}/{{ operational.total_tasks }} ({{ operational.completion_rate | format_percent }})
🎯 **Client Satisfaction:** {{ client_satisfaction.average | format_number }}/5.0
💰 **Net Profit Margin:** {{ financial.net_profit_margin | format_percent }}

---

## Financial Performance

### Revenue Trend
| Week | Revenue | Target | Variance |
|------|---------|--------|----------|
{% for week in financial.weekly_breakdown %}
| **Week {{ week.week }}** | ${{ week.revenue | format_number }} | ${{ week.target | format_number }} | {{ week.variance_pct | format_percent }} |
{% endfor %}
| **Monthly Total** | ${{ financial.total_revenue | format_number }} | ${{ financial.monthly_target | format_number }} | {{ financial.total_variance_pct | format_percent }} |

### Expense Breakdown
| Category | Amount | % of Revenue |
|----------|--------|--------------|
{% for expense in financial.expenses %}
| **{{ expense.category }}** | ${{ expense.amount | format_number }} | {{ expense.percentage_of_revenue | format_percent }} |
{% endfor %}
| **Total Expenses** | ${{ financial.total_expenses | format_number }} | {{ financial.expense_ratio | format_percent }} |

### Key Financial Metrics
- **Gross Margin:** {{ financial.gross_margin | format_percent }}
- **Net Profit:** ${{ financial.net_profit | format_number }}
- **Average Invoice Value:** ${{ financial.avg_invoice_value | format_number }}
- **Collection Rate:** {{ financial.collection_rate | format_percent }}

---

## Operational Excellence

### Project Performance
| Project | Status | Completion | Budget | Actual |
|---------|--------|------------|--------|--------|
{% for project in operational.projects %}
| **{{ project.name }}** | {{ project.status }} | {{ project.completion_pct | format_percent }} | ${{ project.budget | format_number }} | ${{ project.actual | format_number }} |
{% endfor %}

### Team Productivity
- **Tasks Completed:** {{ operational.total_tasks_completed }}
- **Average Completion Time:** {{ operational.avg_completion_time }} days
- **Team Utilization:** {{ operational.team_utilization | format_percent }}
- **Efficiency Score:** {{ operational.efficiency_score | format_number }}/100

### Quality Metrics
- **Error Rate:** {{ quality.error_rate | format_percent }}
- **Client Retention:** {{ quality.client_retention_rate | format_percent }}
- **On-time Delivery:** {{ quality.on_time_delivery_rate | format_percent }}

---

## Social Media & Marketing

### Platform Performance
| Platform | Followers | Engagement | Reach | Conversion |
|----------|-----------|------------|-------|------------|
{% for platform in social.platforms %}
| **{{ platform.name }}** | {{ platform.followers | format_number }} | {{ platform.engagement_rate | format_percent }} | {{ platform.reach | format_number }} | {{ platform.conversion_rate | format_percent }} |
{% endfor %}

### Content Performance
- **Total Posts:** {{ social.total_posts }}
- **Total Engagement:** {{ social.total_engagement | format_number }}
- **Top Performing Content:** {{ social.top_content_type }}
- **Sentiment Score:** {{ social.avg_sentiment | format_number }}/10

---

## Client & Customer Analysis

### Top Clients by Revenue
| Client | Revenue | Projects | Satisfaction |
|--------|--------|----------|--------------|
{% for client in clients.top_by_revenue %}
| **{{ client.name }}** | ${{ client.revenue | format_number }} | {{ client.projects }} | {{ client.satisfaction | format_number }}/5 |
{% endfor %}

### New Business
- **New Clients:** {{ business.new_clients }}
- **New Revenue:** ${{ business.new_revenue | format_number }}
- **Conversion Rate:** {{ business.lead_conversion_rate | format_percent }}
- **Average Deal Size:** ${{ business.avg_deal_size | format_number }}

---

## Strategic Initiatives

### Completed Initiatives
{% for initiative in initiatives.completed %}
✅ **{{ initiative.name }}**
   - Completed: {{ initiative.completion_date }}
   - Impact: {{ initiative.impact }}
   - ROI: {{ initiative.roi | format_percent }}

{% endfor %}

### In Progress
{% for initiative in initiatives.in_progress %}
🔄 **{{ initiative.name }}** ({{ initiative.progress_pct | format_percent }})
   - Expected: {{ initiative.expected_completion }}
   - Status: {{ initiative.status }}

{% endfor %}

---

## Risk & Opportunities

### Risks Identified
{% for risk in risks %}
⚠️ **{{ risk.title }}** ({{ risk.severity }})
   - Description: {{ risk.description }}
   - Mitigation: {{ risk.mitigation }}
   - Owner: {{ risk.owner }}

{% endfor %}

### Opportunities
{% for opportunity in opportunities %}
💡 **{{ opportunity.title }}**
   - Potential: {{ opportunity.potential }}
   - Required: {{ opportunity.requirements }}
   - Timeline: {{ opportunity.timeline }}

{% endfor %}

---

## Next Month Priorities

{% for priority in next_month_priorities %}
{{ loop.index }}. {{ priority }}
{% endfor %}

---

## Financial Projections

### Next Month Forecast
- **Projected Revenue:** ${{ projections.next_month.revenue | format_number }}
- **Projected Expenses:** ${{ projections.next_month.expenses | format_number }}
- **Projected Profit:** ${{ projections.next_month.profit | format_number }}
- **Confidence:** {{ projections.next_month.confidence }}

### Quarterly Outlook
| Quarter | Projected Revenue | Key Initiatives |
|---------|-------------------|-----------------|
{% for quarter in projections.quarterly %}
| **Q{{ quarter.quarter }}** | ${{ quarter.revenue | format_number }} | {{ quarter.key_initiatives }} |
{% endfor %}

---
*Generated by {{ generated_by }} on {{ generated_at }}*
*Next monthly summary: {{ next_report_date }}*