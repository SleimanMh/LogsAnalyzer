import threading
import subprocess
from api import app

def run_watcher():
    print("▶ Starting watcher.py...")
    subprocess.run(["python", "watcher.py"])


def run_api():
    print("🚀 Starting API on port 5000...")
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)


if __name__ == "__main__":
    watcher_thread = threading.Thread(target=run_watcher, daemon=True)
    watcher_thread.start()

    run_api()
