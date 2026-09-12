"""
Configuration settings for LinkedIn Agent
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base directories
BASE_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = BASE_DIR.parent

# File paths - check local folder first, then parent workspace
PROFILE_FILE = (
    BASE_DIR / "candidate-profile.md" if (BASE_DIR / "candidate-profile.md").exists()
    else WORKSPACE_DIR / "candidate-profile.md" if (WORKSPACE_DIR / "candidate-profile.md").exists()
    else BASE_DIR / "candidate-profile.template.md" if (BASE_DIR / "candidate-profile.template.md").exists()
    else WORKSPACE_DIR / "candidate-profile.template.md"
)
PIPELINE_FILE = (
    BASE_DIR / "linkedin-pipeline.md" if (BASE_DIR / "linkedin-pipeline.md").exists()
    else WORKSPACE_DIR / "linkedin-pipeline.md" if (WORKSPACE_DIR / "linkedin-pipeline.md").exists()
    else BASE_DIR / "linkedin-pipeline.template.md" if (BASE_DIR / "linkedin-pipeline.template.md").exists()
    else WORKSPACE_DIR / "linkedin-pipeline.template.md"
)
INSTRUCTIONS_FILE = BASE_DIR / "linkedin-agent.md" if (BASE_DIR / "linkedin-agent.md").exists() else WORKSPACE_DIR / "linkedin-agent.md"

# CV File location (dynamically resolved from candidate-profile.md, or overridden via env)
DEFAULT_CV_PATH = os.getenv("DEFAULT_CV_PATH", "")

# CDP & Browser Settings
CDP_PORT = int(os.getenv("CDP_PORT", "9222"))
CDP_ENDPOINT = f"http://localhost:{CDP_PORT}"
USER_DATA_DIR = Path(os.getenv("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "LinkedInAgent_Profile"
LINKEDIN_FEED_URL = "https://www.linkedin.com/feed/"
LINKEDIN_MESSAGING_URL = "https://www.linkedin.com/messaging/"

# Pacing & Safety Parameters
PAGE_LOAD_WAIT_SEC = 2.5
BEFORE_TYPING_WAIT_SEC = 1.0
HOVER_DELAY_SEC = 0.7
TYPING_DELAY_MS = 60  # ms per character for human-like typing
MAX_CONVERSATIONS_PER_SESSION = 5
MAX_SESSION_MINUTES = 25

# Gemini / LLM API Key (optional, defaults to environment variable)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
DEFAULT_MODEL = os.getenv("LINKEDIN_AGENT_MODEL", "gemini-2.5-flash")
