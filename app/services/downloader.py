import os
from pathlib import Path
import yt_dlp

try:
    import imageio_ffmpeg
    FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_EXE = None

from app.utils.filehandler import create_download_directory


class VideoDownloader:

    def __init__(self, subfolder: str | None = None):
        self.download_dir = create_download_directory(subfolder)

    def _get_format_spec(self, format_type: str, resolution: str) -> str:
        if format_type == "audio":
            return "bestaudio/best"

        resolution_map = {
            "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
            "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
            "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]",
            "360p": "bestvideo[height<=360]+bestaudio/best[height<=360]",
            "worst": "worst",
            "best": "bestvideo+bestaudio/best",
        }
        return resolution_map.get(resolution, "bestvideo+bestaudio/best")

    def download(
        self,
        url: str,
        progress_hook=None,
        format_type: str = "video",
        resolution: str = "best",
        audio_format: str = "mp3",
    ):
        output_template = os.path.join(
            str(self.download_dir),
            "%(title)s.%(ext)s"
        )

        format_spec = self._get_format_spec(format_type, resolution)

        options = {
            "outtmpl": output_template,
            "quiet": True,
            "noplaylist": True,
            "format": format_spec,
        }

        if FFMPEG_EXE:
            options["ffmpeg_location"] = FFMPEG_EXE

        if format_type == "audio":
            options["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": audio_format,
                "preferredquality": "192",
            }]

        if progress_hook:
            options["progress_hooks"] = [progress_hook]

        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(
                url,
                download=True,
            )
            if not info:
                raise RuntimeError("Failed to download video file or format unavailable.")

            filepath = ydl.prepare_filename(info)
            if info.get("_filename") and os.path.exists(info["_filename"]):
                filepath = info["_filename"]
            elif info.get("requested_downloads"):
                for req in info["requested_downloads"]:
                    if req.get("filepath") and os.path.exists(req["filepath"]):
                        filepath = req["filepath"]
                        break



            base_path, _ = os.path.splitext(filepath)

            if format_type == "audio":
                final_audio_path = f"{base_path}.{audio_format}"

                if os.path.exists(filepath) and filepath != final_audio_path:
                    try:
                        os.remove(filepath)
                    except Exception:
                        pass

                for ext in [".mp4", ".webm", ".mkv", ".3gp"]:
                    leftover = f"{base_path}{ext}"
                    if os.path.exists(leftover) and leftover != final_audio_path:
                        try:
                            os.remove(leftover)
                        except Exception:
                            pass

                if os.path.exists(final_audio_path):
                    filepath = final_audio_path

            # Fallback file lookup if prepare_filename differed from merged file
            if not os.path.exists(filepath):
                for ext in [".mp4", ".mkv", ".webm", ".mp3", ".m4a", ".wav", ".flac", ".3gp"]:
                    candidate = f"{base_path}{ext}"
                    if os.path.exists(candidate):
                        filepath = candidate
                        break

            # Ultimate fallback: grab most recently created file in download_dir
            if not os.path.exists(filepath):
                all_files = [
                    f for f in self.download_dir.glob("*")
                    if f.is_file() and not f.name.endswith(".part") and not f.name.endswith(".ytdl")
                ]
                if all_files:
                    latest = max(all_files, key=lambda f: f.stat().st_mtime)
                    filepath = str(latest)

            if not os.path.exists(filepath):
                raise RuntimeError("Video download failed. The video file could not be created or YouTube rate-limited the request.")

            return filepath

