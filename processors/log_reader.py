import os

def read_log_files(logs_dir):
    for file in os.listdir(logs_dir):
        if file.endswith(".log"):
            yield os.path.join(logs_dir, file)
