"""
Global CUE coordination bus.

Garanteix que només una preescolta CUE soni a la vegada en tots els modes
(Editor i DJ). Qualsevol widget que iniciï una CUE avisa al bus, i la resta
de widgets aturen la seva CUE en cours. També s'utilitza per aturar totes
les CUE en canvis de mode (Editor <-> DJ).
"""

import logging

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


class CueBus(QObject):
    """Bus singleton per coordinar la reproducci\u00f3 CUE global."""

    # Senyal emesa quan qualsevol CUE comença a reproduir (porta el filepath)
    cue_started = Signal(str)
    # Senyal emesa quan cal aturar totes les CUE (canvi de mode, etc.)
    cue_stopped = Signal()

    def __init__(self):
        super().__init__()


_instance: CueBus | None = None


def get_cue_bus() -> CueBus:
    """Retorna la inst\u00e0ncia singleton del CueBus."""
    global _instance
    if _instance is None:
        _instance = CueBus()
    return _instance
