from datetime import datetime


def append_timestamp(message):
    return f"({datetime.now().strftime("%H:%M:%S")}) {message}"
