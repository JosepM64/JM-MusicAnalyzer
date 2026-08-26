import logging
import math
import os

import mutagen

from core.formats.base import AudioReader
from core.models import MetadataInfo, MusicFile, TechnicalInfo

logger = logging.getLogger(__name__)


class UniversalReader(AudioReader):
    """
    Universal audio reader using mutagen's auto-detection.
    Supports: MP3, FLAC, OGG, M4A/AAC, WAV, AIFF, APE, TAK, WV, DSF, DSDIFF, Opus, Speex, etc.
    """

    def read(self, use_cache: bool = True, save_db: bool = True) -> MusicFile:
        try:
            if not os.path.exists(self.filepath):
                return MusicFile(self.filepath, error="Archivo no encontrado")

            if use_cache and self.db:
                try:
                    mtime = os.path.getmtime(self.filepath)
                    cached_data = self.db.get_track(self.filepath, mtime=mtime)
                    if cached_data:
                        return self._from_db_row(cached_data)
                except Exception as e:
                    logger.debug(f"Error accediendo a cache: {e}")

            audio = mutagen.File(self.filepath)
            if audio is None:
                return MusicFile(
                    self.filepath, error="Formato no reconocido o archivo corrupto"
                )

            tech = self._extract_technical(audio)
            meta = self._extract_metadata(audio, audio.tags)

            music_file = MusicFile(
                filepath=self.filepath,
                technical=tech,
                metadata=meta,
            )

            if save_db and self.db:
                try:
                    self.db.save_track(music_file)
                except Exception as e:
                    logger.warning(f"No se pudo guardar en DB: {e}")

            return music_file

        except Exception as e:
            logger.error(f"Error leyendo {self.filepath}: {e}")
            return MusicFile(self.filepath, error=str(e))

    def _extract_technical(self, audio) -> TechnicalInfo:
        info = audio.info
        bitrate = getattr(info, "bitrate", 0) or 0
        if bitrate:
            bitrate = int(bitrate / 1000)

        duration = getattr(info, "length", 0) or 0
        file_size = self._get_file_size()
        channels = getattr(info, "channels", 2) or 2
        sample_rate = getattr(info, "sample_rate", 0) or 0

        if bitrate == 0 and duration > 0:
            bitrate = int((file_size * 8) / (duration * 1000))
            logger.debug(
                f"Calculated bitrate from size/duration: {bitrate} kbps for {os.path.basename(self.filepath)}"
            )

        channel_mode = self._get_channel_mode(info)
        file_created, file_modified = self._get_file_times()

        return TechnicalInfo(
            bitrate=bitrate,
            vbr=getattr(info, "bitrate_mode", 0) == 2
            if hasattr(info, "bitrate_mode")
            else False,
            sample_rate=sample_rate,
            channels=channels,
            duration=duration,
            file_size=file_size,
            id3_version=self._get_container_type(audio),
            encoding=self._get_encoding_type(audio),
            channel_mode=channel_mode,
            bitrate_real=bitrate,
            frecuencia_corte=None,
            bitrate_match=True,
            file_created=file_created,
            file_modified=file_modified,
        )

    def _get_channel_mode(self, info) -> str:
        try:
            mode = getattr(info, "channel_mode", None)
            if mode is not None:
                if isinstance(mode, int):
                    modes = {
                        0: "Stereo",
                        1: "Joint Stereo",
                        2: "Dual Channel",
                        3: "Mono",
                    }
                    return modes.get(mode, f"Modo {mode}")
                return str(mode)
            channels = getattr(info, "channels", 0)
            if channels == 1:
                return "Mono"
            if channels == 2:
                return "Estéreo"
            return f"{channels} canales"
        except Exception:
            return "Estéreo"

    def _get_container_type(self, audio) -> str:
        container_name = type(audio).__name__
        return container_name

    def _get_encoding_type(self, audio) -> str:
        container = type(audio).__name__
        encoding_map = {
            "MP3": "MPEG Layer 3",
            "EasyMP3": "MPEG Layer 3",
            "FLAC": "FLAC",
            "OggVorbis": "Ogg Vorbis",
            "OggOpus": "Ogg Opus",
            "OggFLAC": "Ogg FLAC",
            "OggTheora": "Ogg Theora",
            "OggSpeex": "Ogg Speex",
            "M4A": "MPEG-4 AAC",
            "MP4": "MPEG-4",
            "WAVE": "PCM",
            "AIFF": "PCM",
            "ASF": "ASF",
            "APEv2": "APE",
            "MonkeysAudio": "APE",
            "Musepack": "Musepack",
            "OptimFROG": "OptimFROG",
            "TAK": "TAK",
            "TrueAudio": "TTA",
            "WavPack": "WavPack",
            "DSDIFF": "DSD",
            "DSF": "DSD",
        }
        return encoding_map.get(container, container)

    def _extract_metadata(self, audio, tags) -> MetadataInfo:
        def get_t(fid, default=None):
            try:
                if tags is None:
                    return default
                f = tags.get(fid)
                if not f:
                    return default
                if hasattr(f, "text") and f.text:
                    return str(f.text[0])
                try:
                    return str(f[0])
                except (TypeError, IndexError):
                    return str(f)
            except (KeyError, IndexError, AttributeError):
                return default

        title = (
            get_t("TIT2")
            or get_t("title")
            or get_t("\xa3tit")
            or os.path.splitext(os.path.basename(self.filepath))[0]
        )
        artist = (
            get_t("TPE1") or get_t("artist") or get_t("\xa3ART") or get_t("albumartist")
        )
        album = get_t("TALB") or get_t("album") or get_t("\xa3alb")
        genre = get_t("TCON") or get_t("genre") or get_t("\xa3gen")
        year = get_t("TDRC") or get_t("TYER") or get_t("date") or get_t("\xa3day")
        track_number = get_t("TRCK") or get_t("tracknumber") or get_t("\xa3trk")
        comment = self._get_comment(tags)
        bpm = self._parse_int(get_t("TBPM") or get_t("bpm"))

        meta = MetadataInfo(
            title=title,
            artist=artist,
            album=album,
            genre=genre,
            year=str(year) if year else None,
            track_number=str(track_number) if track_number else None,
            bpm=bpm,
            isrc=get_t("TSRC") or get_t("isrc"),
            rating=0,
            comment=comment,
        )

        self._extract_cover(tags, meta)
        self._extract_rating(tags, meta)

        return meta

    def _get_comment(self, tags) -> str | None:
        try:
            if tags is None:
                return None
            comm_frames = tags.getall("COMM")
            if comm_frames:
                return str(comm_frames[0].text[0])
            if hasattr(tags, "comments"):
                return str(tags.comments)
            return None
        except Exception:
            return None

    def _extract_cover(self, tags, meta):
        try:
            if tags is None:
                return
            pictures = getattr(tags, "pictures", None)
            if pictures and len(pictures) > 0:
                self._set_cover_from_frame(meta, pictures[0])
                return

            apic_frames = tags.getall("APIC")
            if apic_frames:
                self._set_cover_from_frame(meta, apic_frames[0])
                return

            for f in tags.values():
                if f.__class__.__name__ == "APIC":
                    self._set_cover_from_frame(meta, f)
                    break
        except Exception as e:
            logger.debug(f"Error extrayendo carátula: {e}")

        if not getattr(meta, "cover_data", None):
            self._extract_cover_from_folder(meta)

    def _set_cover_from_frame(self, meta, frame):
        meta.cover_data = getattr(frame, "data", None)
        meta.cover_mime = getattr(frame, "mime", "image/jpeg")

    def _extract_cover_from_folder(self, meta):
        try:
            folder = os.path.dirname(self.filepath)
            for cand in [
                "cover.jpg",
                "folder.jpg",
                "cover.jpeg",
                "cover.png",
                "AlbumArt.jpg",
                "AlbumArtSmall.jpg",
            ]:
                cand_path = os.path.join(folder, cand)
                if os.path.exists(cand_path):
                    with open(cand_path, "rb") as f:
                        meta.cover_data = f.read()
                    ext = os.path.splitext(cand_path)[1].lower()
                    if ext in (".jpg", ".jpeg"):
                        meta.cover_mime = "image/jpeg"
                    elif ext == ".png":
                        meta.cover_mime = "image/png"
                    else:
                        meta.cover_mime = "image/jpeg"
                    break
        except Exception as e2:
            logger.debug(f"Fallback extra cover load failed: {e2}")

    def _extract_rating(self, tags, meta):
        try:
            if tags is None:
                return
            popm_frames = tags.getall("POPM")
            if popm_frames:
                meta.rating_mixxx = self._map_rating(popm_frames[0].rating)

            for f in tags.getall("TXXX"):
                desc = f.desc.lower()
                try:
                    val = int(float(f.text[0].strip()))
                    if "mediamonkey" in desc or "score" in desc:
                        meta.rating_mm = math.ceil(val / 20)
                    elif "rating" in desc:
                        current_rating = val if 1 <= val <= 5 else self._map_rating(val)
                        if meta.rating_mixxx == 0:
                            meta.rating_mixxx = current_rating
                except (ValueError, IndexError):
                    continue

            meta.rating = (
                meta.rating_mixxx if meta.rating_mixxx > 0 else (meta.rating_mm or 0)
            )
        except Exception:
            pass

    def _map_rating(self, val: int) -> int:
        if val >= 252:
            return 5
        if val >= 196:
            return 4
        if val >= 128:
            return 3
        if val >= 64:
            return 2
        if val >= 1:
            return 1
        return 0

    def _parse_int(self, v):
        try:
            return int(float(str(v).strip()))
        except (ValueError, TypeError):
            return None

    @classmethod
    def _from_db_row(cls, row: dict) -> MusicFile:
        tech = TechnicalInfo(
            bitrate=row["bitrate_header"],
            bitrate_real=row.get("bitrate_real") or row["bitrate_header"],
            vbr=bool(row["vbr"]),
            sample_rate=row["sample_rate"],
            channels=2,
            channel_mode="Estéreo",
            duration=row.get("duration") or 0,
            file_size=row["filesize"],
            id3_version="2.x",
            encoding="MP3",
            frecuencia_corte=row.get("frecuencia_corte"),
            bitrate_match=True,
            file_created=row.get("file_created"),
            file_modified=row.get("file_modified"),
        )

        meta = MetadataInfo(
            title=row["title"],
            artist=row["artist"],
            album=row["album"],
            genre=row["genre"],
            year=row["year"],
            track_number=row["track_number"],
            bpm=row["bpm"],
            isrc=row.get("isrc"),
            rating=row["rating"],
            comment=row["comment"],
        )

        if row.get("cover_data"):
            meta.cover_data = row["cover_data"]
            meta.cover_mime = row.get("cover_mime") or "image/jpeg"

        return MusicFile(
            filepath=row["filepath"],
            technical=tech,
            metadata=meta,
            sha256=row.get("sha256"),
        )
