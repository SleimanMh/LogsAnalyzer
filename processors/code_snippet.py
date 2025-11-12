import os
from config.settings import CODEBASE_DIRS

def find_file_in_codebase(filename):
    """
    Search for a file by name inside configured codebase directories.
    Returns full path if found, otherwise None.
    """
    if not filename:
        return None

    for base in CODEBASE_DIRS:
        if not os.path.exists(base):
            continue

        for root, dirs, files in os.walk(base):
            if filename in files:
                return os.path.join(root, filename)

    return None


def extract_snippet(path, line_no, window=6):
    """
    Extracts code snippet around a given line number.
    Supports fallback search when 'path' does not exist (e.g., Java files).
    """
    if not path:
        return None

    # Normalize relative paths, e.g. "MyService.java"
    filename = os.path.basename(path)

    # ✅ If path does not exist, try to find it in codebase
    if not os.path.exists(path):
        alt = find_file_in_codebase(filename)
        if not alt:
            return None
        path = alt

    # ✅ Now read the file safely
    try:
        with open(path, "r", encoding="utf8") as f:
            lines = f.readlines()

        total = len(lines)
        # Clamp snippet window
        start = max(0, line_no - window - 1)
        end = min(total, line_no + window)

        snippet = ""
        for i in range(start, end):
            snippet += f"{i + 1}: {lines[i]}"

        return snippet

    except Exception as e:
        print(f"⚠️ Failed to extract snippet from {path}: {e}")
        return None
