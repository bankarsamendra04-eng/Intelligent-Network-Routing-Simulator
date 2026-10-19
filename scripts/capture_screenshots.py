import os
import sys
import time
import subprocess
import threading
import urllib.request

# Add current dir to sys.path
sys.path.insert(0, os.path.abspath("."))
from app import create_app

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
SCREENSHOT_DIR = os.path.abspath(os.path.join("docs", "screenshots"))
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

flask_app = create_app()

# 1. Start Flask in background thread
def run_flask():
    flask_app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)

server_thread = threading.Thread(target=run_flask, daemon=True)
server_thread.start()

# 2. Wait for server to come online
print("Waiting for Flask server on http://127.0.0.1:5000 ...")
for _ in range(20):
    try:
        with urllib.request.urlopen("http://127.0.0.1:5000/api/health", timeout=1) as resp:
            if resp.status == 200:
                print("Flask is online.")
                break
    except Exception:
        time.sleep(0.5)

screenshots = [
    ("01-dashboard.png", "http://127.0.0.1:5000/"),
    ("02-custom-topology.png", "http://127.0.0.1:5000/?view=custom"),
    ("03-dijkstra-shortest-path.png", "http://127.0.0.1:5000/?view=dijkstra"),
    ("04-distance-vector-routing.png", "http://127.0.0.1:5000/?view=distance_vector"),
    ("05-link-failure-recovery.png", "http://127.0.0.1:5000/?view=link_failure"),
]

for filename, url in screenshots:
    out_path = os.path.join(SCREENSHOT_DIR, filename)
    print(f"Capturing {filename} from {url} ...")
    cmd = [
        CHROME_PATH,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=3000",
        "--window-size=1600,1020",
        f"--screenshot={out_path}",
        url
    ]
    subprocess.run(cmd, check=True)
    size = os.path.getsize(out_path)
    print(f"Captured {filename} ({size} bytes)")

print("All screenshots captured successfully!")
