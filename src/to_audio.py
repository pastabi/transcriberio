import glob
import os
import subprocess
from pathlib import Path

import yt_dlp


class FFmpegError(Exception):
    pass


def extract_audio(video_path, video_url, full_mp3_output):
    try:
        Path(full_mp3_output).parent.mkdir(parents=True, exist_ok=True)

        source_file = None
        temp_download_file = None

        # 1. Download full audio from url if video file wasn't provided
        if not video_path and video_url.strip():
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": f"{full_mp3_output}_temp.%(ext)s",
                "quiet": True,
                "no_warnings": True,
            }
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(video_url.strip(), download=True)
                    temp_download_file = ydl.prepare_filename(info)
                    source_file = temp_download_file

            except yt_dlp.utils.DownloadError as e:
                raise FFmpegError(f"URL Download Failed: {str(e)}")
            except Exception as e:
                raise FFmpegError(f"yt-dlp Error: {str(e)}")
        else:
            source_file = video_path

        # 2. Run our standard FFmpeg command on whatever source file we have
        mp3_command = [
            "ffmpeg",
            "-i",
            source_file,
            "-vn",
            "-acodec",
            "libmp3lame",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-b:a",
            "32k",
            full_mp3_output,
            "-y",
        ]

        subprocess.run(
            mp3_command,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # 3. Clean up the yt-dlp temporary download file now that we have the MP3
        if temp_download_file and os.path.exists(temp_download_file):
            os.remove(temp_download_file)

        # 4. Create a temporary folder specifically for the chunks
        temp_dir = (
            Path(full_mp3_output).parent / f"temp_chunks_{Path(full_mp3_output).stem}"
        )
        temp_dir.mkdir(parents=True, exist_ok=True)

        # 5. Slice the MP3 we just made into chunks
        chunk_pattern = str(temp_dir / "chunk_%03d.mp3")
        segment_command = [
            "ffmpeg",
            "-i",
            full_mp3_output,
            "-f",
            "segment",
            "-segment_time",
            "5400",
            "-c",
            "copy",
            chunk_pattern,
            "-y",
        ]

        subprocess.run(
            segment_command,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # 6. Get the sorted array of chunks' paths
        chunks = sorted(glob.glob(str(temp_dir / "chunk_*.mp3")))

        if not chunks:
            raise FFmpegError("FFmpeg completed but no audio chunks were found.")

        return chunks, str(temp_dir)

    except subprocess.CalledProcessError as e:
        raise FFmpegError(f"FFmpeg failed: {str(e)}")
    except FFmpegError:
        raise
    except Exception as e:
        raise FFmpegError(f"An unexpected audio extraction error occurred: {str(e)}")
