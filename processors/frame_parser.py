import re

PY_FRAME = re.compile(r'File "(.+?)", line (\d+), in (.+)')

JAVA_FRAME = re.compile(r'at (.+?)\((.+?):(\d+)\)')

def parse_frames(trace):
    frames = []

    for line in trace.splitlines():

        m = PY_FRAME.search(line)
        if m:
            frames.append({
                "path": m.group(1),
                "line": int(m.group(2)),
                "func": m.group(3),
                "lang": "python"
            })
            continue

        j = JAVA_FRAME.search(line)
        if j:
            full_class = j.group(1)
            file = j.group(2)
            line = int(j.group(3))

            frames.append({
                "path": file,
                "line": line,
                "func": full_class,
                "lang": "java"
            })

    return frames
