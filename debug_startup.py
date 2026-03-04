import asyncio
import os
import sys
import traceback
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).parent))

from ai_employee.main import AIEmployeeSystem

async def main():
    print(f"DEBUG: SECRET_KEY in env: '{os.getenv('SECRET_KEY')}'")
    print("Attempting to initialize AIEmployeeSystem...")
    system = AIEmployeeSystem()
    try:
        # Pass .env.local explicitly
        await system.initialize(".env.local")
        print("Success! System initialized.")
    except Exception as e:
        print("\n" + "="*50)
        print("CRITICAL ERROR DURING INITIALIZATION:")
        print("="*50)
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    # Ensure ENVIRONMENT is set
    if "ENVIRONMENT" not in os.environ:
        os.environ["ENVIRONMENT"] = "test"
    
    asyncio.run(main())
