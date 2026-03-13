
import asyncio
import time
import logging
from pathlib import Path
from typing import Callable, Optional, Any

logger = logging.getLogger("RalphLoop")

class RalphLoop:
    """
    Ralph Wiggum Loop Implementation.
    Persistence pattern that keeps an agent or task running until completion.
    """
    
    def __init__(self, 
                 name: str,
                 task_func: Callable, 
                 completion_check: Callable,
                 max_iterations: int = 10,
                 delay: int = 5):
        self.name = name
        self.task_func = task_func
        self.completion_check = completion_check
        self.max_iterations = max_iterations
        self.delay = delay
        self.iterations = 0

    async def run(self, *args, **kwargs) -> bool:
        print(f"\n🔄 [Ralph Loop: {self.name}] Starting...")
        
        while self.iterations < self.max_iterations:
            self.iterations += 1
            print(f"📍 [Iteration {self.iterations}/{self.max_iterations}] Executing task...")
            
            try:
                # Execute the main task
                await self.task_func(*args, **kwargs)
                
                # Check for completion
                if await self.completion_check():
                    print(f"✅ [Ralph Loop: {self.name}] Target condition met. Task COMPLETE.")
                    return True
                
                print(f"⏳ [Ralph Loop: {self.name}] Target not met yet. Re-trying in {self.delay}s...")
                await asyncio.sleep(self.delay)
                
            except Exception as e:
                logger.error(f"Error in Ralph Loop '{self.name}': {e}")
                await asyncio.sleep(self.delay)

        print(f"🛑 [Ralph Loop: {self.name}] Max iterations reached. Task TIMED OUT.")
        return False

# Example condition: Check if a file exists in /Done folder
async def check_file_in_done(filename: str, vault_path: Path) -> bool:
    done_path = vault_path / "Done" / filename
    return done_path.exists()
