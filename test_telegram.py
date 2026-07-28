import os
import sys

# Load local overrides from a gitignored .env file, if present.
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

if not os.environ.get("TELEGRAM_BOT_TOKEN") or not os.environ.get("TELEGRAM_CHAT_ID"):
    sys.exit(
        "Missing TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID.\n"
        "Set them as environment variables, or create a local .env file "
        "(see .env.example) — .env is gitignored and never committed."
    )

# Import and run main
from main import main
main()
