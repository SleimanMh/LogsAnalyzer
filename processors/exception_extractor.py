# processors/exception_extractor.py
import re

# Matches optional ISO timestamp + [LEVEL] prefix, then returns the rest of the line in group(1)
PREFIX = re.compile(r'^\s*\d{4}-\d{2}-\d{2}T[0-9:\.]+(?:Z|[+\-]\d{2}:\d{2})?\s*\[[A-Z]+\]\s+(.*)$')

# Python frame line (works with or without prefixes because we use .search)
FRAME_LINE = re.compile(r'File ".*?", line \d+, in .+')

# Start of Python traceback (helps us enter "collecting" mode even if first line is stripped)
TRACEBACK_START = re.compile(r'Traceback \(most recent call last\):')

# Final exception line (Error/Exception/Throwable/Warning) with optional leading whitespace
EXC_LINE = re.compile(r'^\s*(?:[A-Za-z_][\w\.]*(?:Error|Exception|Throwable|Warning)|'
                      r'(?:UserWarning|DeprecationWarning|RuntimeWarning))\s*:')

# Java frames
JAVA_FRAME = re.compile(r'^\s*at\s+\w+(?:\.\w+)*\([^)]+\)')

class ExceptionExtractor:
    """
    Collects multi-line Python exceptions from log streams that may
    include timestamp/log-level prefixes. Also treats single-line [WARNING]
    messages as lightweight "events" if desired.
    """
    def __init__(self, capture_warnings_as_events: bool = True):
        self.collecting = False
        self.buffer = []
        self.saw_frame = False
        self.capture_warnings_as_events = capture_warnings_as_events

    def _strip_prefix(self, line: str) -> str:
        m = PREFIX.match(line)
        return m.group(1) if m else line

    def feed(self, raw_line: str):
        """
        Feed a single raw log line. Returns a list of completed exception blocks (0..n).
        """
        results = []
        line = raw_line.rstrip("\n")

        # Keep original line for output, but use a prefix-stripped version for pattern checks
        logical = self._strip_prefix(line)

        # Optionally capture single-line warnings as events (not full tracebacks)
        if (not self.collecting) and self.capture_warnings_as_events:
            # e.g. "⚠️ Kaggle credentials not found — using local CSV instead."
            # We use the presence of [WARNING] in the raw prefix as a hint.
            if "[WARNING]" in raw_line and not (FRAME_LINE.search(logical) or JAVA_FRAME.search(logical)):
                results.append(f"{line}")
                return results

        # Enter collecting mode if we see a traceback header, a Python frame, or a Java frame
        if not self.collecting and (TRACEBACK_START.search(logical) or FRAME_LINE.search(logical) or JAVA_FRAME.search(logical)):
            self.collecting = True
            self.buffer = [line]
            self.saw_frame = FRAME_LINE.search(logical) is not None or JAVA_FRAME.search(logical) is not None
            return results

        if self.collecting:
            self.buffer.append(line)

            # Track if we actually saw any frame lines (python or java)
            if FRAME_LINE.search(logical) or JAVA_FRAME.search(logical):
                self.saw_frame = True

            # Heuristics to decide when an exception finished:
            # 1) We see an "exception line" (KeyError:, ValueError:, ... Warning:)
            if EXC_LINE.search(logical):
                # Flush the current buffer as a complete exception
                results.append("\n".join(self.buffer))
                self.buffer = []
                self.collecting = False
                self.saw_frame = False
                return results

            # 2) A blank line AFTER we saw frames often ends a traceback in many loggers
            if self.saw_frame and logical.strip() == "":
                results.append("\n".join(self.buffer))
                self.buffer = []
                self.collecting = False
                self.saw_frame = False
                return results

        return results
