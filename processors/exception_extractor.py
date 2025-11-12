import re

# Python frame example:
PYTHON_FRAME = re.compile(r'^\s*File "(.+?)", line (\d+), in (.+)')

# Java frame example:
# at com.package.Class.method(Class.java:42)
JAVA_FRAME = re.compile(r'^\s*at (.+?)\((.+?):(\d+)\)')

# Java exception start (common patterns)
JAVA_EXCEPTION_START = re.compile(r'^\s*(Exception in thread ".+"|[A-Za-z0-9_.]+Exception:|[A-Za-z0-9_.]+Error:)')

# Python exception end
PYTHON_EXCEPTION_END = re.compile(r'^[A-Za-z_]+Error:|^[A-Za-z_]+Exception:')

class ExceptionExtractor:
    def __init__(self):
        self.collecting = False
        self.buffer = []

    def feed(self, line):
        results = []

        # 1) Detect start of Java or Python exception
        if (
            PYTHON_FRAME.search(line)
            or JAVA_FRAME.search(line)
            or JAVA_EXCEPTION_START.search(line)
        ):
            self.collecting = True
            self.buffer.append(line)
            return results

        # 2) If we are collecting stack trace lines
        if self.collecting:
            self.buffer.append(line)

            # End of Python exception
            if PYTHON_EXCEPTION_END.search(line.strip()):
                results.append("\n".join(self.buffer))
                self.buffer = []
                self.collecting = False

            # End of Java exception when next blank line or new timestamp
            elif line.strip() == "" or line.startswith("202") or line.startswith("["):
                results.append("\n".join(self.buffer))
                self.buffer = []
                self.collecting = False

        return results
