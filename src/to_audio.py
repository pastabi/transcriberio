import glob
import subprocess
from pathlib import Path


class FFmpegError(Exception):
    pass


def extract_audio(video_path, full_mp3_output):
    try:
        # 1. Create the full MP3 file first (for the user download)
        Path(full_mp3_output).parent.mkdir(parents=True, exist_ok=True)

        full_command = f"ffmpeg -i '{video_path}' -vn -acodec libmp3lame -ac 1 -ar 16000 -b:a 32k '{full_mp3_output}' -y"
        subprocess.run(
            full_command,
            shell=True,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # 2. Create a temporary folder specifically for the chunks
        temp_dir = (
            Path(full_mp3_output).parent / f"temp_chunks_{Path(full_mp3_output).stem}"
        )
        temp_dir.mkdir(parents=True, exist_ok=True)

        # 3. Slice the MP3 we just made into chunks (-c copy makes this instant)
        chunk_pattern = str(temp_dir / "chunk_%03d.mp3")

        segment_command = f"ffmpeg -i '{full_mp3_output}' -f segment -segment_time 5400 -c copy '{chunk_pattern}' -y"
        subprocess.run(
            segment_command,
            shell=True,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # 4. Get the sorted array of chanks' paths
        chunks = sorted(glob.glob(str(temp_dir / "chunk_*.mp3")))

        if not chunks:
            raise FFmpegError("FFmpeg completed but no audio chunks were found.")

        # We return the array of chunks AND the temp folder path so we can delete it later
        return chunks, str(temp_dir)

    except subprocess.CalledProcessError as e:
        raise FFmpegError(f"FFmpeg failed: {str(e)}")
    except Exception as e:
        raise FFmpegError(f"An unexpected audio extraction error occurred: {str(e)}")
