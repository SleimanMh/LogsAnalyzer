import re

def canonicalize_exception(trace):
    trace = re.sub(r'0x[0-9A-Fa-f]+', '', trace)
    trace = re.sub(r'/[^/\s]+/([^/\s]+\.py)', r'\1', trace)
    trace = re.sub(r'line \d+', 'line X', trace)
    trace = re.sub(r'\d{4}-\d{2}-\d{2}.*', '', trace)
    return trace.strip()
