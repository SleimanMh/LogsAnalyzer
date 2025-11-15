import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from processors.exception_extractor import ExceptionExtractor
from processors.pipeline import ErrorPipeline
from config.settings import LOGS_DIR

pipeline = ErrorPipeline()
file_positions = {}
extractors = {}


def process_full_file(path):
    """
    Runs a full scan of an existing log file and processes all exceptions.
    """
    print(f"\n📄 Running initial full scan on: {path}")
    extractor = ExceptionExtractor()

    try:
        with open(path, "r", encoding="utf8") as f:
            for line in f:
                for exc in extractor.feed(line):
                    if exc:
                        handle_exception(exc)
        # ✅ Flush any remaining exception at EOF
        leftover = extractor._flush()
        if leftover:
            print("\n🚨 New exception detected (EOF flush):")
            handle_exception(leftover)

    except Exception as e:
        print(f"⚠️ Error reading {path}: {e}")


def process_new_lines(path):
    """
    Processes new log lines when a file changes (incremental mode).
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
    except Exception as e:
        print(f"⚠️ Error reading {path}: {e}")
        return

    for line in new_lines:
        for exc in extractor.feed(line):
            if exc:
                handle_exception(exc)


def handle_exception(exc):
    """
    Common processing function for both full scans and real-time detection.
    """
    print("\n🚨 New exception detected:")
    print(exc)
    result = pipeline.process_exception(exc)
    print("✅ Processed:", result)


class LogDirectoryHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if not event.src_path.endswith(".log"):
            return
        process_new_lines(event.src_path)

    def on_created(self, event):
        if event.src_path.endswith(".log"):
            print(f"🆕 New log file detected: {event.src_path}")
            file_positions[event.src_path] = 0
            extractors[event.src_path] = ExceptionExtractor()


def preload_existing_logs():
    """
    On startup, scan all log files and prepare watchers.
    """
    for file in os.listdir(LOGS_DIR):
        if file.endswith(".log"):
            full_path = os.path.join(LOGS_DIR, file)
            process_full_file(full_path)
            file_positions[full_path] = os.path.getsize(full_path)
            extractors[full_path] = ExceptionExtractor()


if __name__ == "__main__":
    print("📡 Starting directory log watcher...")
    print(f"📁 Watching directory: {LOGS_DIR}")

    preload_existing_logs()

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
