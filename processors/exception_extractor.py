import re

FRAME_LINE = re.compile(r'^\s*File "(.+?)", line (\d+), in (.+)')
EXCEPTION_END = re.compile(r'^[A-Za-z_]+Error:|^[A-Za-z_]+Exception:')

class ExceptionExtractor:
    def __init__(self):
        self.collecting = False
        self.buffer = []

    def feed(self, line):
        results = []

        # Start of traceback inferred from first frame line
        if FRAME_LINE.search(line):
            self.collecting = True
            self.buffer.append(line)
            return results

        if self.collecting:
            self.buffer.append(line)

            if EXCEPTION_END.search(line.strip()):
                results.append("\n".join(self.buffer))
                self.buffer = []
                self.collecting = False

        return results
