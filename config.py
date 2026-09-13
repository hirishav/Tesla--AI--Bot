import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Discord Configuration
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Groq Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not DISCORD_TOKEN:
    print("WARNING: DISCORD_TOKEN is not set in the environment.")

if not GROQ_API_KEY:
    print("WARNING: GROQ_API_KEY is not set in the environment.")
