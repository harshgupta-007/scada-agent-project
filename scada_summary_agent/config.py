import os
from dotenv import load_dotenv

# Load .env from project root
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    # This will help catch config issues early
    raise RuntimeError(
        "GOOGLE_API_KEY is not set. "
        "Add it to your .env file in the project root."
    )
