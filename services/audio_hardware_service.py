import logging

logger = logging.getLogger(__name__)

try:
    from PySide6.QtMultimedia import QAudioDevice, QAudioOutput, QMediaDevices

    _HAS_QTMULTIMEDIA = True
except ImportError:
    logger.warning("QtMultimedia no disponible")
    QMediaDevices = None
    QAudioDevice = None
    QAudioOutput = None
    _HAS_QTMULTIMEDIA = False

_HAS_SOUNDDEVICE = None


def _ensure_sounddevice():
    global _HAS_SOUNDDEVICE
    if _HAS_SOUNDDEVICE is not None:
        return
    try:
        import sounddevice as _

        _HAS_SOUNDDEVICE = True
    except ImportError:
        _HAS_SOUNDDEVICE = False


class AudioHardwareService:
    """
    Gestiona la detección y asignación robusta de hardware de audio.
    Usa sounddevice para enumerar dispositivos porque sounddevice usa índices numéricos
    simples que可以直接 usarse para seleccionar el dispositivo de salida.
    """

    @staticmethod
    def get_output_devices():
        devices = []

        _ensure_sounddevice()
        if _HAS_SOUNDDEVICE:
            try:
                import sounddevice as sd

                sd_devices = sd.query_devices()
                if isinstance(sd_devices, dict):
                    sd_devices = [sd_devices]

                hostapis = sd.query_hostapis()
                wasapi_idx = next(
                    (
                        i
                        for i, h in enumerate(hostapis)
                        if h["name"] == "Windows WASAPI"
                    ),
                    None,
                )
                ds_idx = next(
                    (
                        i
                        for i, h in enumerate(hostapis)
                        if h["name"] == "Windows DirectSound"
                    ),
                    None,
                )

                preferred_hostapis = []
                if wasapi_idx is not None:
                    preferred_hostapis.append(wasapi_idx)
                if ds_idx is not None:
                    preferred_hostapis.append(ds_idx)

                if preferred_hostapis:
                    seen_names = set()
                    for i, dev in enumerate(sd_devices):
                        if (
                            dev.get("max_output_channels", 0) >= 2
                            and dev.get("hostapi", -1) in preferred_hostapis
                        ):
                            base_name = dev.get("name", f"Device {i}").strip()
                            host_name = (
                                hostapis[dev["hostapi"]]["name"]
                                if dev.get("hostapi", -1) < len(hostapis)
                                else ""
                            )
                            short_host = host_name.replace("Windows ", "")
                            display_name = f"{base_name} [{short_host}]"
                            if base_name not in seen_names:
                                seen_names.add(base_name)
                                devices.append(
                                    {
                                        "id": str(i),
                                        "index": i,
                                        "name": display_name,
                                        "backend": "sounddevice",
                                    }
                                )
                else:
                    for i, dev in enumerate(sd_devices):
                        if dev.get("max_output_channels", 0) >= 2:
                            name = dev.get("name", f"Device {i}")
                            devices.append(
                                {
                                    "id": str(i),
                                    "index": i,
                                    "name": name,
                                    "backend": "sounddevice",
                                }
                            )

                logger.info(
                    f"sounddevice: {len(devices)} dispositivos de audio (filtrados)"
                )
                if devices:
                    return devices
            except Exception as e:
                logger.error(f"Error enumerando dispositivos sounddevice: {e}")

        if _HAS_QTMULTIMEDIA:
            try:
                qt_devices = QMediaDevices.audioOutputs()
                for dev in qt_devices:
                    try:
                        dev_id = str(dev.id())
                        devices.append(
                            {
                                "id": dev_id,
                                "name": dev.description() or "Dispositivo Desconocido",
                                "device_obj": dev,
                                "backend": "qtmultimedia",
                            }
                        )
                    except Exception as e:
                        logger.error(f"Error al leer dispositivo Qt: {e}")

                if devices:
                    logger.info(
                        f"QtMultimedia: {len(devices)} dispositivos de audio (fallback)"
                    )
            except Exception as e:
                logger.warning(f"QtMultimedia no disponible: {e}")

        return devices

    @staticmethod
    def find_device_by_id(device_id):
        if not device_id:
            return None

        # Convertir a string para comparación
        device_id_str = str(device_id).strip()

        _ensure_sounddevice()

        # sounddevice: primero intentar por índice numérico
        if _HAS_SOUNDDEVICE and device_id_str.isdigit():
            try:
                import sounddevice as sd

                idx = int(device_id_str)
                sd_dev = sd.query_devices(idx)
                return {
                    "index": idx,
                    "name": sd_dev.get("name", f"Device {idx}"),
                    "backend": "sounddevice",
                }
            except Exception as e:
                logger.warning(f"No se encontró dispositivo sounddevice {idx}: {e}")

        # sounddevice: buscar por nombre parcial (para manejar IDs que cambian)
        if _HAS_SOUNDDEVICE:
            try:
                import sounddevice as sd

                all_devices = sd.query_devices()
                if isinstance(all_devices, dict):
                    all_devices = [all_devices]

                # Guardar el nombre del dispositivo objetivo para hacer match
                target_name = device_id_str.lower()

                for i, dev in enumerate(all_devices):
                    dev_name = dev.get("name", "").lower()
                    # Buscar coincidencia parcial en el nombre
                    if target_name in dev_name or dev_name in target_name:
                        logger.info(
                            f"find_device_by_id: match por nombre '{dev.get('name')}' con índice {i}"
                        )
                        return {
                            "index": i,
                            "name": dev.get("name"),
                            "backend": "sounddevice",
                        }
            except Exception as e:
                logger.error(f"Error buscando dispositivo por nombre: {e}")

        # QtMultimedia usa UUIDs
        if _HAS_QTMULTIMEDIA:
            try:
                for dev in QMediaDevices.audioOutputs():
                    if str(dev.id()) == device_id_str:
                        return {
                            "device_obj": dev,
                            "name": dev.description(),
                            "backend": "qtmultimedia",
                        }
            except Exception:
                pass

        return None
