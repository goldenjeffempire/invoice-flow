import os
import threading
import time
import requests
from urllib.parse import urlparse


def start_keep_alive():
    """
    Start a background thread that pings the app periodically
    to prevent Render's free tier from spinning down.
    """
    render_external_url = os.environ.get("RENDER_EXTERNAL_URL")

    if not render_external_url:
        return
    
    # Validate URL scheme
    try:
        parsed = urlparse(render_external_url)
        if parsed.scheme not in ('http', 'https'):
            return
    except Exception:
        return

    def ping():
        while True:
            try:
                health_url = f"{render_external_url}/health/"
                requests.get(health_url, timeout=10)
            except requests.RequestException:
                pass
            except Exception:
                pass
            time.sleep(600)

    thread = threading.Thread(target=ping, daemon=True)
    thread.start()
