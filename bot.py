import os
import time
from dotenv import load_dotenv
import requests

load_dotenv()
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
MAX_LEN = 2000  # Discord's per-message character limit


def send_message(text: str) -> None:
    """POST `text` to the Discord channel behind the webhook."""
    if not WEBHOOK_URL:
        raise RuntimeError("Set the DISCORD_WEBHOOK_URL environment variable.")

    text = (text or "").strip()
    if not text:
        return  # nothing to send

    resp = requests.post(
        WEBHOOK_URL,
        json={"content": text[:MAX_LEN]},
        timeout=10,
    )

    resp.raise_for_status()


if __name__ == "__main__":
    # Quick connectivity test.
    send_message("stt-bot webhook is connected.")
    print("Sent test message.")
