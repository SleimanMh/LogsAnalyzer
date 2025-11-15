import os
from config.settings import CODEBASE_DIRS

def extract_snippet(path, line_no, window=6):
    """
    Extracts a small snippet of code around a specific line number (1-based index).
    """
    if not os.path.exists(path):
        # Try to locate the file in the codebase
        alt = find_file_in_codebase(os.path.basename(path))
        if alt:
            path = alt
        else:
            return None

    try:
        with open(path, "r", encoding="utf8") as f:
            lines = f.readlines()

        start = max(0, line_no - window - 1)
        end = min(len(lines), line_no + window)
        snippet = "".join(f"{i+1}: {lines[i]}" for i in range(start, end))
        return snippet
    except Exception as e:
        print(f"⚠️ Failed to extract snippet from {path}: {e}")
        return None


def find_file_in_codebase(filename):
    """
    Searches all CODEBASE_DIRS recursively to find a file by name.
    Returns the full absolute path if found, otherwise None.
    """
    for base in CODEBASE_DIRS:
        for root, _, files in os.walk(base):
            if filename in files:
                return os.path.join(root, filename)
    return None
