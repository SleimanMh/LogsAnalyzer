# storage/dataset_writer.py

import os
import csv

class DatasetWriter:

    def __init__(self, path="/app/data/error_dataset.csv"):
        self.path = path

        # Ensure folder exists
        folder = os.path.dirname(path)
        if folder and not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)

        # Create CSV with header if not exists
        if not os.path.exists(path):
            with open(path, "w", newline="", encoding="utf8") as f:
                writer = csv.writer(f)
                writer.writerow(["stack_trace", "code_snippets", "error_class"])

    def append(self, trace, snippets, analysis):
        """
        Save:
            - trace (string)
            - code snippets (concatenated)
            - error class
        """
        code_text = "\n\n".join(s["snippet"] for s in snippets)

        error_class = analysis.get("exception_class", "Unknown")

        with open(self.path, "a", newline="", encoding="utf8") as f:
            writer = csv.writer(f)
            writer.writerow([trace, code_text, error_class])
