import glob
import os
import subprocess
import sys
from pathlib import Path

import yt_dlp


# create custom error class for clearness and easier handling later
class FFmpegError(Exception):
    pass


# Dynamically finds ffmpeg whether running as a script or a compiled app on Windows or Linux
def get_ffmpeg_path():
    # Automatically detect OS: 'nt' is Windows, 'posix' is Linux/Mac
    exe_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"

    # Checks for the attribute "frozen" which indicates that app is running through a bundle, if present; otherwise returns False
    if getattr(sys, "frozen", False):
        # 1. Try PyInstaller's internal folder (_MEIPASS) where libraries etc are stored in a bundle
        if hasattr(sys, "_MEIPASS"):
            meipass_path = os.path.join(sys._MEIPASS, exe_name)
            if os.path.exists(meipass_path):
                return meipass_path

        # 2. Try the same directory as the executable (fallback)
        exe_path = os.path.join(os.path.dirname(sys.executable), exe_name)
        if os.path.exists(exe_path):
            return exe_path

    # Fallback to system PATH if running normally from source
    return exe_name


def extract_audio(video_path, video_url, full_mp3_output):
    try:
        # check if the directory for our .mp3 exists, if no, create it
        Path(full_mp3_output).parent.mkdir(parents=True, exist_ok=True)

        # we need two variables for the possible path, because we would like to delete the temp video downloaded from url, but if the user uploaded file from the computer, ofc we don't want to touch their files
        source_file = None
        temp_download_file = None

        # 1. Download full audio from url if video file wasn't provided
        if not video_path and video_url.strip():
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": f"{full_mp3_output}_temp.%(ext)s",
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
                "ffmpeg_location": get_ffmpeg_path(),
            }
            try:
                # Initialize the yt-dlp downloader context manager using your custom configuration options
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    # Clean up the URL string, trigger the download, and retrieve the video's metadata
                    info = ydl.extract_info(video_url.strip(), download=True)
                    # Generate the exact absolute file path and filename using the retrieved metadata
                    # We will delete this file later
                    temp_download_file = ydl.prepare_filename(info)
                    # Pass the file path over to the source_file variable, because all further operations will be universal both to user's uploaded file and to downloaded audio
                    source_file = temp_download_file
            # specific error for yt_dlp
            except yt_dlp.utils.DownloadError as e:
                raise FFmpegError(f"URL Download Failed: {str(e)}")
            except Exception as e:
                raise FFmpegError(f"yt-dlp Error: {str(e)}")
        else:
            # this is why we have temp_download_file, because source_file can be a user's file path, we don't want to touch it, but at the same time we would need to delete audio downloaded from url
            source_file = video_path

        # get the ffmpeg path depending on how app is running (directly as .py or in a bundle as executable)
        ffmpeg_exe = get_ffmpeg_path()

        # 2. Run our standard FFmpeg command on whatever source file we have
        # using array of options over string for safety (to avoid command injection via string variable)
        # we compressing audio here to the minimum possible state for clear voice recognition, because the model will anyway do this, but this way we save of the file size we send to API, so we can send much much longer audios in one go (because limit is 25MB per request)
        mp3_command = [
            ffmpeg_exe,
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
        # %03d pattern will name chanks chunk_000.mp3, chunk_001.mp3, etc.
        chunk_pattern = str(temp_dir / "chunk_%03d.mp3")
        segment_command = [
            ffmpeg_exe,
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
        # glob.glob searches for the file with the patter we provide and put them in a list and sorted() sorts them so chunk_000.mp3 comes first in a list
        chunks = sorted(glob.glob(str(temp_dir / "chunk_*.mp3")))

        if not chunks:
            raise FFmpegError("FFmpeg completed but no audio chunks were found.")

        return chunks, str(temp_dir)

    # specific error for ffmpeg
    except subprocess.CalledProcessError as e:
        raise FFmpegError(f"FFmpeg failed: {str(e)}")
    except FFmpegError:
        raise
    except Exception as e:
        raise FFmpegError(f"An unexpected audio extraction error occurred: {str(e)}")
