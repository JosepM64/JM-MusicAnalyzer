import logging
import os
import sys
import time
from typing import Any

import acoustid
import musicbrainzngs
import requests

from config.api_keys import ACOUSTID_API_KEY

logger = logging.getLogger(__name__)

try:
    import JM_MusicAnalizer

    APP_VERSION = JM_MusicAnalizer.APP_VERSION
except ImportError:
    APP_VERSION = "4.43.0"

USER_AGENT = f"JM-MusicAnalyzer/{APP_VERSION} (josep@jmmusic.com)"
musicbrainzngs.set_useragent("JM-MusicAnalyzer", APP_VERSION, "josep@jmmusic.com")


class MusicBrainzProvider:
    def search_by_text(
        self, artist: str = None, title: str = None, duration: float = None
    ) -> dict[str, Any] | None:
        try:
            query = ""
            if artist:
                query += f'artist:"{artist}" '
            if title:
                query += f'recording:"{title}" '
            if not query:
                return None

            time.sleep(1.0)
            res = musicbrainzngs.search_recordings(query=query, limit=5)
            recordings = res.get("recording-list", [])
            if not recordings:
                return None

            best = recordings[0]
            if duration:
                target_ms = duration * 1000
                best = min(
                    recordings,
                    key=lambda x: (
                        abs(int(x.get("length", 0)) - target_ms)
                        if x.get("length")
                        else float("inf")
                    ),
                )
            return self._format_result(best)
        except Exception as e:
            logger.error(f"MusicBrainz text search error: {e}")
        return None

    def search_by_mbid(self, mbid: str) -> dict[str, Any] | None:
        try:
            time.sleep(1.0)
            res = musicbrainzngs.get_recording_by_id(
                mbid, includes=["releases", "artists", "isrcs"]
            )
            rec = res["recording"]
            result = self._format_result(rec)
            isrcs = rec.get("isrc-list", [])
            if isrcs:
                result["isrc"] = isrcs[0]
            return result
        except Exception as e:
            logger.error(f"MusicBrainz MBID lookup error: {e}")
        return None

    def search_by_isrc(self, isrc: str) -> dict[str, Any] | None:
        try:
            time.sleep(1.0)
            res = musicbrainzngs.get_recordings_by_isrc(
                isrc, includes=["artists", "releases"]
            )
            rec_list = res.get("isrc", {}).get("recording-list", [])
            if rec_list:
                return self._format_result(rec_list[0])
        except Exception as e:
            logger.error(f"MusicBrainz ISRC lookup error: {e}")
        return None

    def _format_result(self, rec: dict) -> dict:
        releases = rec.get("release-list", [])
        release = releases[0] if releases else {}
        artist_credits = rec.get("artist-credit", [])
        artist = rec.get("artist-credit-phrase") or (
            artist_credits[0].get("artist", {}).get("name", "Desconocido")
            if artist_credits
            else "Desconocido"
        )
        return {
            "title": rec.get("title"),
            "artist": artist,
            "album": release.get("title"),
            "year": release.get("date", "")[:4] if release.get("date") else None,
            "source": "MusicBrainz",
            "mbid": rec.get("id"),
            "isrc": None,
        }


class ItunesProvider:
    def search(
        self, artist: str = None, title: str = None, duration: float = None
    ) -> dict[str, Any] | None:
        term = f"{artist or ''} {title or ''}".strip()
        if not term:
            return None
        try:
            # URL-encode the search term to handle special characters
            import urllib.parse

            encoded_term = urllib.parse.quote(term)
            url = f"https://itunes.apple.com/search?term={encoded_term}&media=music&limit=5"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                for res in data.get("results", []):
                    if duration and res.get("trackTimeMillis"):
                        if abs(res["trackTimeMillis"] - (duration * 1000)) > 8000:
                            continue
                    return {
                        "title": res.get("trackName"),
                        "artist": res.get("artistName"),
                        "album": res.get("collectionName"),
                        "year": res.get("releaseDate", "")[:4]
                        if res.get("releaseDate")
                        else None,
                        "cover_url": res.get("artworkUrl100", "").replace(
                            "100x100", "600x600"
                        ),
                        "genre": res.get("primaryGenreName"),
                        "track_number": res.get("trackNumber"),
                        "source": "iTunes",
                        "isrc": None,
                    }
        except Exception as e:
            logger.error(f"iTunes search error: {e}")
        return None


class OnlineMetadataService:
    def __init__(self, mb_provider=None, itunes_provider=None):
        self.mb = mb_provider or MusicBrainzProvider()
        self.itunes = itunes_provider or ItunesProvider()
        self.fpcalc_path = self._find_fpcalc()

    def _find_fpcalc(self) -> str | None:
        if getattr(sys, "frozen", False):
            base = os.path.dirname(sys.executable)
            internal = os.path.join(base, "_internal")
            candidates = [
                os.path.join(internal, "tools", "fpcalc.exe"),
                os.path.join(base, "tools", "fpcalc.exe"),
                os.path.join(base, "fpcalc.exe"),
                os.path.join(internal, "fpcalc.exe"),
            ]
        else:
            root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            candidates = [os.path.join(root, "tools", "fpcalc.exe")]

        for c in candidates:
            if os.path.isfile(c):
                logger.info(f"fpcalc encontrado en: {c}")
                return c

        logger.warning(f"fpcalc.exe no encontrado. Rutas buscadas: {candidates}")
        return None

    def _do_fingerprint(self, filepath: str) -> tuple[str, float]:
        """Genera fingerprint per un fitxer d'audio."""
        if not self.fpcalc_path:
            raise RuntimeError("fpcalc.exe no encontrado")

        import subprocess

        cmd = [self.fpcalc_path, "-json", filepath]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f"fpcalc fallo: {result.stderr}")

        import json

        data = json.loads(result.stdout)
        return data.get("fingerprint", ""), float(data.get("duration", 0))

    def search_by_text(
        self, artist: str, title: str, duration: float = None
    ) -> dict[str, Any] | None:
        """Cerca per text (artist + title) a MusicBrainz i iTunes."""
        if not artist and not title:
            return None

        result = self.mb.search_by_text(artist, title, duration)
        if result:
            self._enrich_with_itunes(result, duration)
            return result

        result = self.itunes.search(artist, title, duration)
        return result

    def identify_by_fingerprint(
        self, filepath: str, duration: float = None
    ) -> tuple[dict[str, Any] | None, str]:
        """Identifica canco per fingerprint acoustic (AcoustID + MusicBrainz).
        Returns (result, status_message)."""
        logger.info(
            f"identify_by_fingerprint: filepath={filepath}, duration={duration}"
        )
        if not filepath or not os.path.exists(filepath):
            logger.warning(f"Archivo no existe: {filepath}")
            return None, "Archivo no existe"

        if not self.fpcalc_path:
            logger.warning("fpcalc_path es None")
            return None, "fpcalc.exe no encontrado en tools/"

        if not ACOUSTID_API_KEY:
            logger.warning("ACOUSTID_API_KEY no configurada")
            return (
                None,
                "AcoustID API key no configurada.\nEdita config/api_keys.py o define la variable ACOUSTID_API_KEY",
            )

        logger.info(f"Generando fingerprint con: {self.fpcalc_path}")
        try:
            fingerprint, fp_duration = self._do_fingerprint(filepath)
            logger.info(
                f"Fingerprint generado: {len(fingerprint)} chars, duracion={fp_duration}s"
            )
        except Exception as e:
            logger.error(f"Error generando fingerprint: {e}", exc_info=True)
            return None, f"Error generando fingerprint: {e}"

        logger.info("Consultando AcoustID con fingerprint...")
        try:
            time.sleep(1.0)
            results = acoustid.lookup(
                ACOUSTID_API_KEY,
                fingerprint,
                fp_duration,
                meta="recordings releases artists isrcs",
            )
            logger.info(
                f"AcoustID response type: {type(results).__name__}, keys: {list(results.keys()) if isinstance(results, dict) else 'N/A'}"
            )
        except Exception as e:
            logger.error(f"Error consultando AcoustID: {e}", exc_info=True)
            return None, f"Error consultando AcoustID: {e}"

        # acoustid.lookup retorna dict: {'status': 'ok', 'results': [...]} o {'status': 'error', 'error': '...'}
        if isinstance(results, dict):
            if results.get("status") == "error":
                error_msg = results.get("error", "Unknown error")
                logger.error(f"AcoustID API error: {error_msg}")
                return None, f"Error AcoustID API: {error_msg}"
            results_list = results.get("results", [])
        else:
            results_list = results if results else []

        if not results_list:
            return None, "Sin resultados en AcoustID"

        logger.info(f"AcoustID matches: {len(results_list)}")
        best = results_list[0]
        score = best.get("score", 0)
        recording = best.get("recordings", [{}])[0] if best.get("recordings") else {}

        if not recording:
            return (
                None,
                f"AcoustID encontro huella pero sin grabacion (score: {score:.0%})",
            )

        mbid = recording.get("id")
        if mbid:
            result = self.mb.search_by_mbid(mbid)
        else:
            result = None

        if not result:
            artist = (
                recording.get("artists", [{}])[0].get("name", "")
                if recording.get("artists")
                else ""
            )
            title = recording.get("title", "")
            if artist or title:
                result = self.mb.search_by_text(artist, title, duration)
            else:
                return None, f"Sin datos de grabacion (score: {score:.0%})"

        if result:
            isrcs = recording.get("isrcs", [])
            if isrcs and not result.get("isrc"):
                result["isrc"] = isrcs[0]
            self._enrich_with_itunes(result, duration)
            return result, f"Identificado por fingerprint (score: {score:.0%})"

        return None, "No se pudieron obtener metadatos de MusicBrainz"

    def _enrich_with_itunes(self, result: dict, duration: float = None):
        if result.get("source") == "MusicBrainz" and not result.get("cover_url"):
            itunes_result = self.itunes.search(
                result.get("artist"), result.get("title"), duration
            )
            if itunes_result:
                result["cover_url"] = itunes_result.get("cover_url")
                if not result.get("genre"):
                    result["genre"] = itunes_result.get("genre")
                if not result.get("track_number"):
                    result["track_number"] = itunes_result.get("track_number")
