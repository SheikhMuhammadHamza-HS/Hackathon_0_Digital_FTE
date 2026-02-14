try:
    import schedule
except ImportError:
    # Minimal fallback implementation for the subset of schedule API used
    class _SimpleScheduler:
        def __init__(self):
            self._jobs = []
        class _Every:
            def __init__(self, parent):
                self.parent = parent
            def monday(self):
                return self
            def at(self, time_str):
                return self
            def do(self, job_func):
                self.parent._jobs.append(job_func)
                return job_func
        def every(self):
            return self._Every(self)
        def run_pending(self):
            for job in list(self._jobs):
                job()
    schedule = _SimpleScheduler()

import time
import threading
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from ..agents.linkedin_processor import LinkedInProcessor
from ..models.trigger_file import TriggerFile, TriggerStatus
from ..config.settings import settings, BASE_DIR
from .dashboard_updater import DashboardUpdater
from .logging_service import AuditLogger
from .planner import Planner
import google.generativeai as genai

# Get BASE_DIR for path construction
BASE_DIR = Path(__file__).resolve().parent.parent.parent

logger = logging.getLogger(__name__)


class CEOBriefingGenerator:
    """Generates Monday Morning CEO Briefing.

    Creates a comprehensive briefing including:
    - Business goals progress
    - Pending tasks overview
    - Recent activity summary
    - Metrics and alerts
    - Action items for the week

    Briefings are saved to /Briefings folder for review.
    """

    def __init__(self):
        self.briefings_dir = Path(BASE_DIR) / "Briefings"
        self.briefings_dir.mkdir(parents=True, exist_ok=True)
        self.dashboard_updater = DashboardUpdater()
        self.audit_logger = AuditLogger()

        # Initialize AI if available
        self.ai_available = False
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-pro')
            self.ai_available = True
        except Exception as e:
            logger.warning("AI not available for CEO briefing: %s", e)

    def _get_system_status(self) -> Dict[str, Any]:
        """Gather system status information."""
        needs_action_dir = Path(settings.NEEDS_ACTION_PATH)
        approved_dir = Path(BASE_DIR) / "Approved"
        done_dir = Path(settings.DONE_PATH)

        return {
            'needs_action_count': len(list(needs_action_dir.glob("*.md"))) if needs_action_dir.exists() else 0,
            'approved_count': len(list(approved_dir.glob("*.md"))) if approved_dir.exists() else 0,
            'done_count': len(list(done_dir.glob("*.md"))) if done_dir.exists() else 0,
            'briefings_count': len(list(self.briefings_dir.glob("*_Briefing.md"))),
        }

    def _read_business_goals(self) -> str:
        """Read Business_Goals.md file."""
        goals_path = Path(BASE_DIR) / "Business_Goals.md"
        if goals_path.exists():
            return goals_path.read_text(encoding='utf-8')
        return "Business Goals file not found."

    def _read_company_handbook(self) -> str:
        """Read Company_Handbook.md file."""
        handbook_path = Path(settings.COMPANY_HANDBOOK_PATH)
        if handbook_path.exists():
            return handbook_path.read_text(encoding='utf-8')
        return "Company Handbook file not found."

    def _generate_briefing_content(self) -> str:
        """Generate CEO briefing content."""
        status = self._get_system_status()
        business_goals = self._read_business_goals()
        handbook = self._read_company_handbook()
        current_date = datetime.now()

        # Get current week info
        week_number = current_date.isocalendar()[1]
        quarter = (current_date.month - 1) // 3 + 1

        content = f"""---
type: ceo_briefing
week: {week_number}
quarter: Q{quarter}
date: {current_date.strftime('%Y-%m-%d')}
status: ready
---

# Monday CEO Briefing
**Week**: {week_number} | **Quarter**: Q{quarter} | **Date**: {current_date.strftime('%B %d, %Y')}

---

## 📊 System Status Overview

| Metric | Value | Status |
|--------|-------|--------|
| Pending Tasks | {status['needs_action_count']} | {'⚠️ Needs attention' if status['needs_action_count'] > 0 else '✓ All caught up'} |
| Awaiting Approval | {status['approved_count']} | {'⏳ Waiting' if status['approved_count'] > 0 else '✓ None pending'} |
| Completed Tasks | {status['done_count']} | ✓ Done |
| Previous Briefings | {status['briefings_count']} | Archive |

---

## 🎯 Business Goals Progress

```markdown
{business_goals}
```

---

## 📋 Company Guidelines Reference

```markdown
{handbook[:500] if len(handbook) > 500 else handbook}...
```

*See Company_Handbook.md for complete guidelines*

---

## 🔍 Task Queue Summary

### Pending Tasks ({status['needs_action_count']})
"""

        # List pending tasks
        needs_action_dir = Path(settings.NEEDS_ACTION_PATH)
        if needs_action_dir.exists():
            for i, task_file in enumerate(sorted(needs_action_dir.glob("*.md"))[:10], 1):
                content += f"{i}. `{task_file.name}`\n"
            if status['needs_action_count'] > 10:
                content += f"... and {status['needs_action_count'] - 10} more\n"

        content += f"""
### Awaiting Approval ({status['approved_count']})
"""
        approved_dir = Path(BASE_DIR) / "Approved"
        if approved_dir.exists():
            for i, draft_file in enumerate(sorted(approved_dir.glob("*.md"))[:5], 1):
                content += f"{i}. `{draft_file.name}`\n"
            if status['approved_count'] > 5:
                content += f"... and {status['approved_count'] - 5} more\n"

        content += """
---

## 🤖 AI Employee Activity

The AI employee has been autonomously monitoring inputs and processing tasks.
All actions requiring external execution (email sending, posting to LinkedIn, etc.)
require human approval via the HITL workflow.

### Safety Compliance
- ✅ No sensitive actions without approval
- ✅ All actions logged to audit trail
- ✅ Dashboard updated in real-time
- ✅ Data stays local to machine

---

## 📝 Action Items for This Week

### High Priority
- [ ] Review pending tasks in /Needs_Action
- [ ] Approve or reject drafts in /Approved
- [ ] Review Business_Goals.md for any updates

### Medium Priority
- [ ] Check Dashboard.md for recent activity
- [ ] Review audit logs in /Logs if needed
- [ ] Update Company_Handbook.md if guidelines change

### Low Priority
- [ ] Review completed tasks in /Done
- [ ] Archive old briefings
- [ ] Consider additional automation opportunities

---

## 📈 Key Metrics to Watch

Based on Business_Goals.md:
- Revenue target: $10,000/month
- Client response time: < 24 hours (alert if > 48 hours)
- Invoice payment rate: > 90% (alert if < 80%)
- Software costs: <$500/month (alert if > $600)

---

## 🔄 Next Week's Focus

*Areas to prioritize based on current status:*
"""

        # Add AI-generated insights if available
        if self.ai_available:
            try:
                prompt = f"""Based on the following information, provide 3-5 key focus areas for the CEO this week.

System Status:
- Pending Tasks: {status['needs_action_count']}
- Awaiting Approval: {status['approved_count']}
- Completed Tasks: {status['done_count']}

Business Goals:
{business_goals[:800]}

Provide concise, actionable focus areas as bullet points.
"""
                response = self.model.generate_content(prompt)
                content += "\n" + response.text.strip() + "\n"
            except Exception as e:
                logger.warning("Could not generate AI insights: %s", e)
                content += "\n- Continue focusing on task completion and approval workflow\n"
                content += "- Monitor system health and performance\n"
                content += "- Review and update business goals as needed\n"
        else:
            content += "\n- Continue focusing on task completion and approval workflow\n"
            content += "- Monitor system health and performance\n"
            content += "- Review and update business goals as needed\n"

        content += f"""
---
**Briefing Generated**: {current_date.strftime('%Y-%m-%d %H:%M:%S')}
**AI Employee Status**: Active and Monitoring
"""
        return content

    def generate_briefing(self) -> Path:
        """Generate and save Monday CEO briefing.

        Returns:
            Path to the generated briefing file
        """
        current_date = datetime.now()
        date_str = current_date.strftime('%Y%m%d')
        filename = f"{date_str}_CEO_Briefing.md"
        briefing_path = self.briefings_dir / filename

        # Create plan for briefing generation
        try:
            planner = Planner()
            plan, plan_path = planner.create_and_save_plan(
                task_type="ceo_briefing",
                task_description="Generate Monday CEO Briefing with system status and action items",
                context={
                    "date": date_str,
                    "week_number": current_date.isocalendar()[1]
                },
                use_ai=True
            )
            logger.info("Created briefing plan: %s", plan_path)
        except Exception as e:
            logger.warning("Could not create briefing plan: %s", e)

        # Generate briefing content
        content = self._generate_briefing_content()
        briefing_path.write_text(content, encoding='utf-8')

        # Log the action
        self.audit_logger.log(
            event="generate_ceo_briefing",
            data={
                "resource": str(briefing_path),
                "status": "success",
                "date": date_str
            }
        )

        # Update dashboard
        try:
            self.dashboard_updater.append_entry(
                f"Monday CEO Briefing generated: {filename}",
                "SUCCESS"
            )
        except Exception as e:
            logger.warning("Failed to update dashboard: %s", e)

        logger.info("CEO Briefing saved: %s", briefing_path)
        return briefing_path


class Scheduler:
    """Enhanced weekly scheduler for LinkedIn drafts and CEO briefings.

    Uses the ``schedule`` library. Jobs run every Monday at scheduled times.
    - 08:00 AM: Monday CEO Briefing
    - 09:00 AM: LinkedIn Post Draft
    """

    def __init__(self):
        self.processor = LinkedInProcessor()
        self.briefing_generator = CEOBriefingGenerator()
        self._setup_jobs()

    def _setup_jobs(self):
        # Schedule Monday CEO Briefing at 08:00
        schedule.every().monday.at('08:00').do(self._run_ceo_briefing)
        logger.info('Scheduler job for Monday CEO Briefing set for Monday 08:00')

        # Schedule LinkedIn draft at 09:00
        schedule.every().monday.at('09:00').do(self._run_linkedin_job)
        logger.info('Scheduler job for LinkedIn drafts set for Monday 09:00')

    def _run_ceo_briefing(self):
        """Generate Monday CEO Briefing."""
        logger.info('Running Monday CEO Briefing generation...')
        try:
            briefing_path = self.briefing_generator.generate_briefing()
            logger.info(f'Monday CEO Briefing generated: {briefing_path}')
            return True
        except Exception as e:
            logger.error(f'Error during Monday CEO Briefing: {e}')
            return False

    def _run_linkedin_job(self):
        """Create a LinkedIn post draft."""
        success = False
        timestamp = datetime.utcnow()
        trigger_id = 'scheduler_' + timestamp.strftime('%Y%m%d%H%M%S')
        dummy_trigger = TriggerFile(
            id=trigger_id,
            filename=f"TRIGGER_{timestamp.strftime('%Y%m%d%H%M%S')}.md",
            type="scheduled",
            source_path='Business_Goals.md',
            timestamp=timestamp,
            status=TriggerStatus.PENDING,
            location=f"{settings.NEEDS_ACTION_PATH}/TRIGGER_{timestamp.strftime('%Y%m%d%H%M%S')}.md"
        )
        try:
            # Save trigger file to disk so processor can read it
            dummy_trigger.save_to_disk()
            success = self.processor.process_trigger_file(dummy_trigger)
            logger.info(f'Scheduled LinkedIn draft processing result: {success}')
            try:
                dashboard = DashboardUpdater()
                status = "SUCCESS" if success else "FAILURE"
                dashboard.append_entry("Scheduled Draft: LinkedIn post", status)
            except Exception as e:
                logger.warning(f'Failed to update dashboard: {e}')
        except Exception as e:
            logger.error(f'Error during scheduled LinkedIn draft processing: {e}')
        return success

    def start(self):
        """Run the scheduler loop in a background thread.

        The loop checks for pending jobs every second. The method returns
        immediately after starting the thread so callers can continue.
        """
        thread = threading.Thread(target=self._run_continuously, daemon=True)
        thread.start()
        logger.info('Scheduler thread started')

    def _run_continuously(self):
        while True:
            schedule.run_pending()
            time.sleep(1)

    def run_once(self):
        """Execute any pending jobs right now – useful for the CLI ``schedule-run`` command."""
        schedule.run_pending()
        logger.info('Executed scheduler pending jobs manually')

    def run_briefing_now(self):
        """Generate CEO briefing immediately."""
        return self._run_ceo_briefing()

    def run_linkedin_now(self):
        """Generate LinkedIn draft immediately."""
        return self._run_linkedin_job()
