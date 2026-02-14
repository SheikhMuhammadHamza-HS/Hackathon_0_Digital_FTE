"""
Planner Service - Generates Plan.md files for complex reasoning tracking.

Creates detailed reasoning plans before executing tasks, following the
hackathon requirement for "Claude reasoning loop that creates Plan.md files".

Plans are stored in /Plans directory and referenced during task execution.
"""
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
import json

import sys
from pathlib import Path as PathLib

# Import BASE_DIR from settings module
BASE_DIR = PathLib(__file__).resolve().parent.parent.parent

from ..config.settings import settings
from ..utils.file_utils import ensure_directory_exists
from ..utils.security import is_safe_path
import google.generativeai as genai

logger = logging.getLogger(__name__)


class Plan:
    """Represents a reasoning plan for a task.

    Contains the thought process, steps, and decision rationale.
    """

    def __init__(
        self,
        plan_id: str,
        task_type: str,
        task_description: str,
        context: Optional[Dict[str, Any]] = None
    ):
        self.plan_id = plan_id
        self.task_type = task_type
        self.task_description = task_description
        self.context = context or {}
        self.steps: List[Dict[str, Any]] = []
        self.reasoning: str = ""
        self.alternatives_considered: List[Dict[str, str]] = []
        self.risks: List[str] = []
        self.created_at = datetime.now()

    def add_step(self, step_num: int, description: str, reasoning: str = "") -> None:
        """Add a step to the plan."""
        self.steps.append({
            'step': step_num,
            'description': description,
            'reasoning': reasoning
        })

    def add_alternative(self, description: str, reason_for_rejection: str) -> None:
        """Add an alternative approach that was considered."""
        self.alternatives_considered.append({
            'description': description,
            'rejected_because': reason_for_rejection
        })

    def add_risk(self, risk: str, mitigation: str = "") -> None:
        """Add a risk to the plan."""
        self.risks.append({
            'risk': risk,
            'mitigation': mitigation
        })

    def to_markdown(self) -> str:
        """Convert plan to markdown format."""
        timestamp = self.created_at.isoformat()

        md = f"""---
type: plan
id: "{self.plan_id}"
task_type: "{self.task_type}"
created_at: "{timestamp}"
status: active
---

# Plan: {self.plan_id}

## Task Description
{self.task_description}

## Context
"""
        for key, value in self.context.items():
            md += f"- **{key}**: {value}\n"

        md += f"""
## Reasoning
{self.reasoning}

## Execution Steps
"""
        for step in self.steps:
            md += f"""### Step {step['step']}: {step['description']}
{step['reasoning']}

"""

        if self.alternatives_considered:
            md += """## Alternatives Considered
"""
            for alt in self.alternatives_considered:
                md += f"- **{alt['description']}**: Rejected because {alt['rejected_because']}\n"
            md += "\n"

        if self.risks:
            md += """## Risks and Mitigations
"""
            for risk in self.risks:
                md += f"- **Risk**: {risk['risk']}\n"
                if risk['mitigation']:
                    md += f"  *Mitigation*: {risk['mitigation']}\n"
            md += "\n"

        md += f"""
---
*Plan generated at {timestamp}*
"""
        return md


class Planner:
    """Generates reasoning plans using AI.

    Uses Gemini API to generate detailed plans for tasks before execution.
    Plans are saved as Plan.md files for audit and transparency.
    """

    def __init__(self, plans_dir: Optional[Path] = None):
        """Initialize the planner service.

        Args:
            plans_dir: Directory to save plans (defaults to /Plans)
        """
        self.plans_dir = Path(plans_dir or BASE_DIR / "Plans")
        ensure_directory_exists(self.plans_dir)

        # Initialize Gemini if available
        self.gemini_available = False
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
            self.gemini_available = True
            logger.info("Planner initialized with Gemini API")
        except Exception as e:
            logger.warning("Gemini API not available for planning: %s", e)
            logger.info("Plans will use template-based generation")

    def _generate_plan_id(self, task_type: str) -> str:
        """Generate a unique plan ID."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"{task_type}_{timestamp}"

    def _generate_reasoning_with_gemini(
        self,
        task_type: str,
        task_description: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Use Gemini to generate reasoning for a task.

        Returns:
            Dictionary with reasoning, steps, alternatives, risks
        """
        if not self.gemini_available:
            return self._generate_template_reasoning(task_type, task_description, context)

        prompt = f"""You are an AI planning assistant. Create a detailed reasoning plan for the following task.

Task Type: {task_type}
Task Description: {task_description}

Context:
{json.dumps(context, indent=2)}

Generate a structured plan with:
1. **Reasoning**: Explain your thought process and why this approach is chosen
2. **Steps**: List 3-7 specific execution steps with reasoning for each
3. **Alternatives**: Mention 1-2 alternative approaches and why they were rejected
4. **Risks**: Identify 2-3 potential risks and mitigation strategies

Return your response as a JSON object with this structure:
{{
  "reasoning": "string",
  "steps": [{{"step": 1, "description": "string", "reasoning": "string"}}, ...],
  "alternatives": [{{"description": "string", "rejected_because": "string"}}, ...],
  "risks": [{{"risk": "string", "mitigation": "string"}}, ...]
}}
"""

        try:
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()

            # Try to parse JSON from response
            if '```json' in result_text:
                result_text = result_text.split('```json')[1].split('```')[0].strip()
            elif '```' in result_text:
                result_text = result_text.split('```')[1].split('```')[0].strip()

            return json.loads(result_text)

        except Exception as e:
            logger.error("Failed to generate reasoning with Gemini: %s", e)
            return self._generate_template_reasoning(task_type, task_description, context)

    def _generate_template_reasoning(
        self,
        task_type: str,
        task_description: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate template-based reasoning without AI."""
        return {
            "reasoning": f"Using template-based approach for {task_type}. The task requires {task_description}.",
            "steps": [
                {
                    "step": 1,
                    "description": "Analyze the task requirements and context",
                    "reasoning": "Understanding the full scope before execution prevents errors"
                },
                {
                    "step": 2,
                    "description": "Gather necessary information and resources",
                    "reasoning": "Having all inputs ready ensures smooth execution"
                },
                {
                    "step": 3,
                    "description": "Execute the primary task action",
                    "reasoning": "This is the core action that fulfills the user's request"
                },
                {
                    "step": 4,
                    "description": "Verify the result and handle any errors",
                    "reasoning": "Quality assurance ensures the outcome meets requirements"
                }
            ],
            "alternatives": [
                {
                    "description": "Manual execution",
                    "rejected_because": "Automated approach is more efficient and consistent"
                }
            ],
            "risks": [
                {
                    "risk": "External API failure",
                    "mitigation": "Implement retry logic and error handling"
                },
                {
                    "risk": "Invalid input data",
                    "mitigation": "Validate all inputs before processing"
                }
            ]
        }

    def create_plan(
        self,
        task_type: str,
        task_description: str,
        context: Optional[Dict[str, Any]] = None,
        use_ai: bool = True
    ) -> Plan:
        """Create a reasoning plan for a task.

        Args:
            task_type: Type of task (email, linkedin, whatsapp, file, etc.)
            task_description: Description of what needs to be done
            context: Additional context information
            use_ai: Whether to use AI for reasoning generation

        Returns:
            Plan object with reasoning steps
        """
        plan_id = self._generate_plan_id(task_type)
        context = context or {}

        if use_ai:
            reasoning_data = self._generate_reasoning_with_gemini(
                task_type,
                task_description,
                context
            )
        else:
            reasoning_data = self._generate_template_reasoning(
                task_type,
                task_description,
                context
            )

        plan = Plan(plan_id, task_type, task_description, context)
        plan.reasoning = reasoning_data.get("reasoning", "")

        for step in reasoning_data.get("steps", []):
            plan.add_step(
                step.get("step", len(plan.steps) + 1),
                step.get("description", ""),
                step.get("reasoning", "")
            )

        for alt in reasoning_data.get("alternatives", []):
            plan.add_alternative(
                alt.get("description", ""),
                alt.get("rejected_because", "")
            )

        for risk in reasoning_data.get("risks", []):
            plan.add_risk(
                risk.get("risk", ""),
                risk.get("mitigation", "")
            )

        return plan

    def save_plan(self, plan: Plan) -> Path:
        """Save a plan to a Plan.md file.

        Args:
            plan: Plan object to save

        Returns:
            Path to the saved plan file
        """
        filename = f"{plan.plan_id}_Plan.md"
        file_path = self.plans_dir / filename

        # Safety: ensure file stays within plans_dir
        if not is_safe_path(str(file_path), str(self.plans_dir)):
            raise ValueError(f"Unsafe plan path: {file_path}")

        file_path.write_text(plan.to_markdown(), encoding='utf-8')
        logger.info("Plan saved: %s", filename)

        return file_path

    def create_and_save_plan(
        self,
        task_type: str,
        task_description: str,
        context: Optional[Dict[str, Any]] = None,
        use_ai: bool = True
    ) -> tuple[Plan, Path]:
        """Create and save a plan in one step.

        Args:
            task_type: Type of task
            task_description: Description of task
            context: Additional context
            use_ai: Whether to use AI for reasoning

        Returns:
            Tuple of (Plan object, path to saved file)
        """
        plan = self.create_plan(task_type, task_description, context, use_ai)
        file_path = self.save_plan(plan)
        return plan, file_path

    def load_plan(self, plan_id: str) -> Optional[Plan]:
        """Load a plan from file.

        Args:
            plan_id: ID of the plan to load

        Returns:
            Plan object or None if not found
        """
        files = list(self.plans_dir.glob(f"{plan_id}_Plan.md"))
        if not files:
            logger.warning("Plan not found: %s", plan_id)
            return None

        # For now, just return the path reference
        # Full parsing could be implemented if needed
        logger.info("Plan loaded: %s", files[0])
        return files[0]

    def get_recent_plans(self, limit: int = 10) -> List[Path]:
        """Get list of recent plan files.

        Args:
            limit: Maximum number of plans to return

        Returns:
            List of plan file paths sorted by modification time
        """
        plans = list(self.plans_dir.glob("*_Plan.md"))
        plans.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return plans[:limit]


# Convenience functions for common task types
def create_email_plan(
    subject: str,
    sender: str,
    content_preview: str,
    company_handbook_context: str = ""
) -> tuple[Plan, Path]:
    """Create a plan for email reply drafting."""
    planner = Planner()
    return planner.create_and_save_plan(
        task_type="email_reply",
        task_description=f"Draft a reply to email from {sender} with subject '{subject}'",
        context={
            "sender": sender,
            "subject": subject,
            "content_preview": content_preview[:200] + "..." if len(content_preview) > 200 else content_preview,
            "company_guidelines": company_handbook_context[:500] if company_handbook_context else ""
        }
    )


def create_linkedin_plan(
    business_goals: str,
    recent_metrics: Dict[str, Any]
) -> tuple[Plan, Path]:
    """Create a plan for LinkedIn post generation."""
    planner = Planner()
    return planner.create_and_save_plan(
        task_type="linkedin_post",
        task_description="Create a professional LinkedIn post about business updates",
        context={
            "business_goals": business_goals,
            "metrics": recent_metrics
        }
    )


def create_file_processing_plan(
    file_path: str,
    file_type: str,
    file_content_preview: str = ""
) -> tuple[Plan, Path]:
    """Create a plan for file processing."""
    planner = Planner()
    return planner.create_and_save_plan(
        task_type="file_processing",
        task_description=f"Process {file_type} file: {file_path}",
        context={
            "file_path": file_path,
            "file_type": file_type,
            "content_preview": file_content_preview[:200] if file_content_preview else ""
        }
    )