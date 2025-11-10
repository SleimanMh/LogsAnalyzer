import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from processors.exception_extractor import ExceptionExtractor
from processors.pipeline import ErrorPipeline
from config.settings import LOGS_DIR

pipeline = ErrorPipeline()

# Stores last read position
file_positions = {}

# Stores separate extractors per file
extractors = {}


def process_full_file(path):
    """
    ✅ Phase 1: Process entire existing log file (like main.py)
    """
    print(f"\n📄 Running initial full scan on: {path}")

    extractor = ExceptionExtractor()
    extractors[path] = extractor

    file_positions[path] = 0  # start from top

    try:
        with open(path, "r", encoding="utf8") as f:
            lines = f.readlines()
            file_positions[path] = f.tell()
    except Exception as e:
        print(f"⚠️ Could not read {path}: {e}")
        return

    for line in lines:
        exceptions = extractor.feed(line)
        for exc in exceptions:
            print("\n🚨 Initial exception detected:")
            print(exc)
            result = pipeline.process_exception(exc)
            print("✅ Processed:", result)


def process_new_lines(path):
    """
    ✅ Phase 2: Incremental processing (tail -f)
    """
    global file_positions, extractors

    if path not in file_positions:
        file_positions[path] = 0
        extractors[path] = ExceptionExtractor()

    extractor = extractors[path]
    last_pos = file_positions[path]

    try:
        with open(path, "r", encoding="utf8") as f:
            f.seek(last_pos)
            new_lines = f.readlines()
            file_positions[path] = f.tell()
    except:
        return

    for line in new_lines:
        exceptions = extractor.feed(line)
        for exc in exceptions:
            print("\n🚨 New exception detected:")
            print(exc)
            result = pipeline.process_exception(exc)
            print("✅ Processed:", result)


class LogDirectoryHandler(FileSystemEventHandler):

    def on_modified(self, event):
        if event.src_path.endswith(".log"):
            process_new_lines(event.src_path)

    def on_created(self, event):
        if event.src_path.endswith(".log"):
            print(f"🆕 New log file detected: {event.src_path}")
            process_full_file(event.src_path)  # full scan on new file


def preload_existing_logs():
    """
    ✅ Before watching directory:
       - Process ALL existing .log files fully
       - Initialize extractor + offset
    """
    for file in os.listdir(LOGS_DIR):
        if file.endswith(".log"):
            full_path = os.path.join(LOGS_DIR, file)
            process_full_file(full_path)


if __name__ == "__main__":
    print("📡 Starting directory log watcher...")
    print(f"📁 Watching directory: {LOGS_DIR}")

    # ✅ Phase 1: full scan
    preload_existing_logs()

    # ✅ Phase 2: incremental real-time watch
    event_handler = LogDirectoryHandler()
    observer = Observer()
    observer.schedule(event_handler, LOGS_DIR, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()
