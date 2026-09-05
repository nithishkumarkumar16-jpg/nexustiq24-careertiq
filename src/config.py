from pathlib import Path
import os

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
KB_DIR = ROOT_DIR / "knowledge_base"
DB_PATH = DATA_DIR / "support.db"
EMBEDDING_CACHE_PATH = DATA_DIR / "embedding_cache.json"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
EMBEDDING_MODEL = "gemini-embedding-001"
GEMINI_MODEL = "gemini-3.5-flash-lite"
DEFAULT_PORT = 8000
