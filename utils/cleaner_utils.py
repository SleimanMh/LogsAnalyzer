import re

def clean_trace_context(text):
    """Minify traceback or snippet without losing semantic meaning."""
    
    # Remove blank lines
    text = "\n".join(line for line in text.splitlines() if line.strip())

    # Remove leading indentation
    cleaned = []
    for line in text.split("\n"):
        cleaned.append(line.lstrip())
    text = "\n".join(cleaned)
    
    # Collapse multiple spaces → single
    text = re.sub(r"[ ]{2,}", " ", text)

    # Collapse multiple newlines → one
    text = re.sub(r"\n{2,}", "\n", text)

    # Trim whitespace around
    text = text.strip()

    return text


def clean_snippet(snippet):
    """Smaller cleaning appropriate for code blocks."""
    # remove blank lines
    snippet = "\n".join(l for l in snippet.splitlines() if l.strip())

    # remove indentation
    snippet = "\n".join(l.lstrip() for l in snippet.splitlines())

    # collapse extra spaces
    snippet = re.sub(r"[ ]{2,}", " ", snippet)

    return snippet.strip()
