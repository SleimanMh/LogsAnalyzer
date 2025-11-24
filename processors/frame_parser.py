import os
import re

FRAME_LINE = re.compile(r'File "(.+?)", line (\d+), in (.+)')

def parse_frames(trace):
    """
    Parses Python traceback frames and returns them from TOP to BOTTOM.
    The first frame is the user function where the exception originated.
    """
    frames = []
    for match in FRAME_LINE.finditer(trace):
        frames.append({
            "path": match.group(1).strip(),
            "line": int(match.group(2)),
            "func": match.group(3).strip(),
        })

    # Reverse → first frame is the real origin
    return list(reversed(frames))


# ============================================================
#   NEW — FUNCTION RESOLUTION LOGIC
# ============================================================

FUNC_DEF_RE = re.compile(r"^\s*(async\s+def|def)\s+(\w+)\s*\(")

def _function_in_file(func_name: str, path: str) -> bool:
    """Return True if the file contains a def func_name(...)."""
    if not func_name or not os.path.exists(path):
        return False

    pattern = re.compile(
        rf"^\s*(async\s+def|def)\s+{re.escape(func_name)}\s*\(",
        re.UNICODE
    )

    try:
        with open(path, "r", encoding="utf8") as f:
            for line in f:
                if pattern.match(line):
                    return True
    except:
        pass

    return False


def _locate_function_in_codebase(func_name: str, codebase_dirs):
    """
    Search all codebase directories for def func_name(...).
    Returns (path, line_number) or None.
    """
    if not func_name:
        return None

    pattern = re.compile(
        rf"^\s*(async\s+def|def)\s+{re.escape(func_name)}\s*\(",
        re.UNICODE
    )

    # Walk codebase
    for base in codebase_dirs:
        base_dir = base.replace("\\", "/")
        if not os.path.isdir(base_dir):
            continue

        for root, dirs, files in os.walk(base_dir):
            for fname in files:
                if not fname.endswith(".py"):
                    continue

                fpath = os.path.join(root, fname)

                try:
                    with open(fpath, "r", encoding="utf8") as f:
                        for lineno, line in enumerate(f, start=1):
                            if pattern.match(line):
                                print(f"🔎 Found {func_name} in {fpath}:{lineno}")
                                return fpath, lineno
                except:
                    continue

    return None


def resolve_frame_location(frame, codebase_dirs):
    """
    Given a raw frame (path, line, func),
    return the *true* (path, line) where the function actually lives.
    """
    func = frame.get("func")
    path = frame.get("path")
    line = frame.get("line")

    # Case 1 — file exists and contains the function → OK
    if os.path.exists(path) and _function_in_file(func, path):
        return path, line

    # Case 2 — function NOT in that file → search codebase
    found = _locate_function_in_codebase(func, codebase_dirs)
    if found:
        return found  # (correct_path, correct_line)

    # Case 3 — fallback: try locating file by basename
    base = os.path.basename(path)
    for base_dir in codebase_dirs:
        for root, dirs, files in os.walk(base_dir):
            if base in files:
                return os.path.join(root, base), line

    # Default — return original values
    return path, line
