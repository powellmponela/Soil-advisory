from pathlib import Path
import os
import secrets

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = Path(os.getenv("SOIL_ADVISORY_PROJECT_ROOT", BASE_DIR)).resolve()
USERNAME = os.getenv("SOIL_ADVISORY_USERNAME", "admin")
PASSWORD = os.getenv("SOIL_ADVISORY_PASSWORD")
SESSION_SECRET = os.getenv("SOIL_ADVISORY_SESSION_SECRET") or secrets.token_urlsafe(32)
STAFF_ENABLED = bool(os.getenv("SOIL_ADVISORY_PASSWORD") and os.getenv("SOIL_ADVISORY_SESSION_SECRET"))
PUBLISHED_DIR = BASE_DIR / "published"
PUBLIC_PREDICTIONS = PUBLISHED_DIR / "predictions.csv"
PRIVATE_AREAS = {
    "data": PROJECT_ROOT / "Data",
    "scripts": PROJECT_ROOT / "scripts",
    "outputs": PROJECT_ROOT / "outputs",
    "models": PROJECT_ROOT / "models",
}
