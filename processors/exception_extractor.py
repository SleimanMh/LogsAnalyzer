import re

TIMESTAMP_PREFIX = re.compile(
    r'^\s*\d{4}-\d{2}-\d{2}T[0-9:\.]+(?:Z|[+\-]\d{2}:\d{2})?\s*\[[A-Z]+\]'
)

FRAME_LINE = re.compile(r'^\s*File ".*?", line \d+, in .+')
EXC_LINE = re.compile(r'^\s*[A-Za-z_][\w\.]*(Error|Exception)\s*:?')
WARN_LINE = re.compile(r'^\s*[A-Za-z_][\w\.]*Warning\s*:?')


class ExceptionExtractor:
    def __init__(self):
        self.current = []
        self.has_frame = False
        self.has_exc = False

    def _reset(self):
        self.current = []
        self.has_frame = False
        self.has_exc = False

    def _is_single_line_exception(self, line: str) -> bool:
        # [ERROR] xxx
        if "[ERROR]" in line:
            return True

        # python exception in one line
        logical = TIMESTAMP_PREFIX.sub("", line).strip()
        if EXC_LINE.match(logical):
            return True

        return False

    def _is_single_line_warning(self, line: str) -> bool:
        # `[WARNING] None` → not a real event
        if "[WARNING]" in line and "None" not in line:
            return True
        return False

    def _flush_if_exception(self):
        if not self.current:
            return None

        block = "\n".join(self.current)

        # multi-line traceback
        if self.has_frame or self.has_exc:
            return block

        # single-line exception
        if self._is_single_line_exception(self.current[0]):
            return block

        # single-line warning event
        if self._is_single_line_warning(self.current[0]):
            return block

        return None

    def feed(self, raw_line: str):
        results = []
        line = raw_line.rstrip("\n")

        is_timestamp = TIMESTAMP_PREFIX.match(line) is not None

        if is_timestamp:
            flushed = self._flush_if_exception()
            if flushed:
                results.append(flushed)

            self._reset()
            self.current.append(line)

        else:
            if not self.current:
                self.current = [line]
            else:
                self.current.append(line)

        # trace recognition
        if FRAME_LINE.search(line):
            self.has_frame = True

        if EXC_LINE.search(line):
            self.has_exc = True
            # flush immediately on final python error
            flushed = self._flush_if_exception()
            if flushed:
                results.append(flushed)
                self._reset()

        return results

    def finalize(self):
        flushed = self._flush_if_exception()
        self._reset()
        return [flushed] if flushed else []
