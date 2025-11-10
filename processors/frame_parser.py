import re

FRAME_LINE = re.compile(r'File "(.+?)", line (\d+), in (.+)')

def parse_frames(trace):
    frames = []
    for m in FRAME_LINE.finditer(trace):
        frames.append({
            "path": m.group(1),
            "line": int(m.group(2)),
            "func": m.group(3)
        })
    return frames
