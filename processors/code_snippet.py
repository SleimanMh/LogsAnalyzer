import os

def extract_snippet(path, line_no, window=6):
    if not os.path.exists(path):
        return None

    try:
        with open(path, "r", encoding="utf8") as f:
            lines = f.readlines()

        start = max(0, line_no - window - 1)
        end = min(len(lines), line_no + window)

        return "".join(f"{i+1}: {lines[i]}" for i in range(start, end))
    except:
        return None
