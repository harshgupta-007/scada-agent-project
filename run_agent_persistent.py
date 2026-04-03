import asyncio
import logging
import sys
from google.adk.sessions.sqlite_session_service import SqliteSessionService
from google.adk.runners import Runner
from scada_summary_agent.agent import root_agent
from google.genai import types
from google.adk.utils.context_utils import Aclosing

# Configure logging - Set to WARNING to reduce noise
logging.basicConfig(level=logging.WARNING)

async def main():
    try:
        # 1. Initialize Persistence Layer
        session_service = SqliteSessionService(db_path="scada_session.db")

        # 2. Initialize the Runner
        app_name = "agents"  # Aligned with root_agent default
        runner = Runner(
            agent=root_agent,
            app_name=app_name,
            session_service=session_service
        )

        # 3. Define Session Context
        user_id = "local_user"
        session_id = "default_session"

        # 4. Create Session if it doesn't exist
        session = await session_service.get_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id
        )
        if not session:
            print(f"Creating new session: {session_id}")
            session = await session_service.create_session(
                app_name=app_name,
                user_id=user_id,
                session_id=session_id
            )
        else:
            print(f"Resuming existing session: {session_id}")

        print(f"Starting SCADA Agent with persistence (Session ID: {session_id})")
        print("Type 'exit' or 'quit' to stop.")
        print("-" * 50)

        while True:
            user_input = await asyncio.to_thread(input, "You: ")
            if user_input.lower() in ["exit", "quit"]:
                break

            print("Agent: ", end="", flush=True)
            
            # 5. Run the Agent
            async with Aclosing(runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=types.Content(role="user", parts=[types.Part(text=user_input)])
            )) as agen:
                async for event in agen:
                    # Print content from the agent (or model)
                    if event.author != "user" and event.content:
                        for part in event.content.parts:
                            if part.text:
                                print(part.text, end="", flush=True)
            
            print("\n" + "-" * 50)

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
