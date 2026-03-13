
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_employee.utils.ralph_loop import RalphLoop

async def mock_agent_work():
    """Simulates an AI agent working on a task."""
    print("   🤖 Agent is thinking and writing files...")
    # In a real scenario, this would call Claude Code or another agent
    await asyncio.sleep(1)

async def check_completion():
    """Simulates checking if a specific 'DONE' marker exists."""
    # For demo, we check if a temporary file exists
    marker = Path("Vault/Workflow/Done/target_task.md")
    if marker.exists():
        return True
    
    # Simulate progress: create the file on the 3rd iteration
    iteration_count_file = Path("temp_iteration_count.txt")
    count = 0
    if iteration_count_file.exists():
        count = int(iteration_count_file.read_text())
    
    count += 1
    iteration_count_file.write_text(str(count))
    
    if count >= 3:
        print("    Simulation: Task actually finished now. Creating DONE marker...")
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("# Completed Task\nDone via Ralph Loop demo.")
        if iteration_count_file.exists():
            os.remove(iteration_count_file)
        return True
        
    return False

async def main():
    print("--- 🚀 RALPH WIGGUM LOOP DEMO ---")
    print("Task: Process a complex multi-step operation")
    
    # Clean up previous runs
    marker = Path("Vault/Workflow/Done/target_task.md")
    if marker.exists(): os.remove(marker)
    
    loop = RalphLoop(
        name="MultiStepTask",
        task_func=mock_agent_work,
        completion_check=check_completion,
        max_iterations=5,
        delay=2
    )
    
    success = await loop.run()
    
    if success:
        print("\n🏆 DEMO SUCCESSFUL: The Ralph Loop ensured the agent kept working until done.")
    else:
        print("\n❌ DEMO FAILED: Task did not complete.")

if __name__ == "__main__":
    asyncio.run(main())
