import subprocess
from pathlib import Path


class FFmpegError(Exception):
    pass


def extract_audio(video_path, mp3_output):
    try:
        Path(mp3_output).parent.mkdir(parents=True, exist_ok=True)
        command = f"ffmpeg -i '{video_path}' -vn -acodec libmp3lame -ac 1 -ar 16000 -b:a 32k '{mp3_output}' -y"
        subprocess.run(
            command,
            shell=True,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError as e:
        raise FFmpegError(f"FFmpeg failed to convert the video: {str(e)}")
    except Exception as e:
        raise FFmpegError(f"An unexpected audio extraction error occurred: {str(e)}")
