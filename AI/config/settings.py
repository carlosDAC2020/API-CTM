import os
from dotenv import load_dotenv

load_dotenv()
print("🔑 Variables de entorno cargadas.")

# --- API Keys ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
BRAVE_SEARCH_API_KEY = os.getenv("BRAVE_SEARCH_API_KEY")

# --- Model & Tool Configurations ---
GEMINI_MODEL_NAME = "gemini-1.5-flash"
TAVILY_MAX_RESULTS = 1
BRAVE_SEARCH_COUNT = 1