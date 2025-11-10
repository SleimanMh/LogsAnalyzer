def shorten_trace(trace, max_lines=40):
    lines = trace.splitlines()
    if len(lines) <= max_lines:
        return trace
    return "\n".join(lines[:20] + ["... (trace shortened) ..."] + lines[-20:])
