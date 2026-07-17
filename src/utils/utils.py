import os
import shutil

from datetime import datetime


def append_timestamp(message):
    return f"({datetime.now().strftime("%H:%M:%S")}) {message}"


def cleanup_temp_dirs(temp_dirs):
    for temp_dir in temp_dirs:
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
    temp_dirs.clear()
