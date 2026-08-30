"""Descàrrega d'àudio des de YouTube amb yt-dlp (API Python)."""

import logging
import os
import sys
from pathlib import Path

import yt_dlp

from PySide6.QtCore import QThread, Signal

logger = logging.getLogger(__name__)


def _get_ffmpeg() -> str | None:
    """Retorna el path a ffmpeg, buscant primer a l'entorn frozen."""
    if getattr(sys, "frozen", False):
        candidates = [
            Path(sys._MEIPASS) / "tools" / "ffmpeg.exe",  # noqa: SLF001
        ]
    else:
        project_tools = (
            Path(__file__).resolve().parent.parent.parent / "tools" / "ffmpeg.exe"
        )
        candidates = [
            project_tools,  # canonical des de v4.50 (mateix binari que l'EXE)
            Path.home() / ".spotdl" / "ffmpeg.exe",  # compat amb l'antic spotDL
        ]
    for c in candidates:
        if c.exists():
            _add_ffmpeg_to_path(str(c))
            return str(c)
    return "ffmpeg"


def _add_ffmpeg_to_path(ffmpeg_path: str):
    """Afegeix el directori de ffmpeg al PATH per a yt-dlp."""
    ff_dir = str(Path(ffmpeg_path).parent)
    current = os.environ.get("PATH", "")
    if ff_dir not in current:
        os.environ["PATH"] = f"{ff_dir};{current}"


def _format_duration(seconds: int | float) -> str:
    """Formata segons a HH:MM:SS o MM:SS."""
    if not seconds:
        return ""
    secs_int = int(seconds)
    hours = secs_int // 3600
    minutes = (secs_int % 3600) // 60
    secs = secs_int % 60
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def search_youtube(query, max_results=15):
    """Cerca vídeos a YouTube usant l'API Python de yt-dlp.

    Si `query` és una URL de YouTube, l'extreu directament en lloc de cercar-la.
    """
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",
        "ignoreerrors": True,
    }
    is_url = (
        query.startswith("http://")
        or query.startswith("https://")
        or "youtube.com" in query
        or "youtu.be" in query
    )
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            if is_url:
                info = ydl.extract_info(query, download=False)
            else:
                info = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
            if not info:
                return []
            entries = info.get("entries") or [info]
            results = []
            for entry in entries:
                if entry is None:
                    continue
                duration = entry.get("duration_string") or _format_duration(entry.get("duration") or 0)
                results.append({
                    "id": entry["id"],
                    "title": entry.get("title", ""),
                    "duration": duration,
                    "url": f"https://www.youtube.com/watch?v={entry['id']}",
                })
            return results
    except Exception as e:
        logger.error("search_youtube: %s", e)
        return []


class DownloadWorker(QThread):
    """Thread per descarregar àudio amb yt-dlp (API Python)."""

    progress = Signal(int, str)
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, urls, output_dir, audio_format="mp3", audio_quality="0"):
        super().__init__()
        self.urls = urls
        self.output_dir = output_dir
        self.audio_format = audio_format
        self.audio_quality = audio_quality
        self._cancelled = False

    def run(self):
        downloaded = []
        total = len(self.urls)
        ffmpeg = _get_ffmpeg()

        for i, url in enumerate(self.urls):
            if self._cancelled:
                break

            self.progress.emit(
                int((i / total) * 100), f"Descarregant {i + 1}/{total}...",
            )

            try:
                result_path = self._download_single(url, ffmpeg)
                if result_path:
                    downloaded.append(result_path)
            except Exception as e:
                self.error.emit(f"Error descarregant {url}: {e}")

        self.finished.emit(downloaded)

    def _download_single(self, url, ffmpeg):
        output_pattern = str(Path(self.output_dir) / "%(title)s.%(ext)s")

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": output_pattern,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": self.audio_format,
                "preferredquality": self.audio_quality,
            }],
            "ffmpeg_location": ffmpeg,
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": True,
            "progress_hooks": [lambda d: self._on_progress(d)],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=True)
                if info and info.get("title"):
                    return str(Path(self.output_dir) / f"{info['title']}.{self.audio_format}")
            except Exception as e:
                raise RuntimeError(str(e)) from e
        return None

    def _on_progress(self, d):
        if self._cancelled:
            raise KeyboardInterrupt

    def cancel(self):
        self._cancelled = True


class PreviewDownloader(QThread):
    """Baixa els primers 30s d'un vídeo de YouTube a MP3 temporal."""

    preview_ready = Signal(str)
    error_ocurred = Signal(str)

    def __init__(self, video_url, temp_dir):
        super().__init__()
        self.video_url = video_url
        self.temp_dir = temp_dir
        self._cancelled = False

    def _progress_hook(self, d):
        if self._cancelled:
            raise KeyboardInterrupt

    def run(self):
        try:
            ffmpeg = _get_ffmpeg()
            output = str(Path(self.temp_dir) / "preview.%(ext)s")

            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": output,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "0",
                }],
                "ffmpeg_location": ffmpeg,
                "quiet": True,
                "no_warnings": True,
                "ignoreerrors": True,
                "download_ranges": lambda info, ydl: [{"start_time": 0, "end_time": 30}],
                "force_keyframes_at_cuts": True,
                "progress_hooks": [self._progress_hook],
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.video_url])

            if self._cancelled:
                return

            expected = Path(self.temp_dir) / "preview.mp3"
            if expected.exists():
                self.preview_ready.emit(str(expected))
                return

            mp3_files = sorted(Path(self.temp_dir).glob("*.mp3"))
            if mp3_files:
                self.preview_ready.emit(str(mp3_files[0]))
                return

            self.error_ocurred.emit("No s'ha pogut generar la previsualització")
        except Exception as e:
            self.error_ocurred.emit(str(e))

    def cancel(self):
        self._cancelled = True
