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

    return list(reversed(frames))
