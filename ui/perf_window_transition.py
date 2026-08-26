import logging
import os
import time

from PySide6.QtCore import Qt, QTimer

logger = logging.getLogger(__name__)


class PerfTransitionMixin:
    def _on_skip_now(self):
        """Salta la canción preparada en el plato destino y carga la siguiente."""
        if self._transition_in_progress:
            return
        if not self._playlist_tracks or self._playlist_index >= len(
            self._playlist_tracks
        ):
            logger.info("[SKIP] No hay más canciones para saltar")
            return

        # Determinar el plato destino (el que no está sonando actualmente)
        if self.crossfader.value() < 0:
            to_deck_obj = self.deck_b
        else:
            to_deck_obj = self.deck_a

        # La próxima pista a cargar es la que está en el índice actual de la playlist
        next_path = self._playlist_tracks[self._playlist_index]
        logger.info(
            f"[SKIP] Saltando pista preparada en deck {to_deck_obj.name}, cargando: {os.path.basename(next_path)}"
        )

        try:
            to_deck_obj.load_file(next_path, False)
        except Exception as e:
            logger.error(f"[SKIP] Error cargando canción: {e}")
            return

        # Eliminar esta pista de la lista visual y avanzar el índice
        self.playlist_widget.remove_top_track()
        self._playlist_index += 1

        if self._playlist_index >= len(self._playlist_tracks):
            logger.info("[SKIP] No quedan más canciones después de saltar")

    def _on_loop_toggle(self, checked):
        """Activar/desactivar loop visual mode - Efectes visuals als decks."""
        if checked:
            self.btn_loop.setText("🔁 LOOP ON")
            self.btn_loop.setStyleSheet("""
                QPushButton {
                    background-color: #00aa00; color: white; font-weight: bold; font-size: 11px;
                    border-radius: 3px;
                }
            """)
            # Iniciar Loop Visual Mode
            self._start_loop_visual_mode()
            logger.info("LOOP Visual Mode: Activado")
        else:
            self.btn_loop.setText("🔁 LOOP")
            self.btn_loop.setStyleSheet("""
                QPushButton {
                    background-color: #333; color: #888; font-weight: bold; font-size: 11px;
                    border-radius: 3px; border: 1px solid #444;
                }
            """)
            logger.info("LOOP: Desactivado")

    def _start_loop_visual_mode(self):
        """Inicia el mode visual LOOP - animació de 15 segons."""
        if hasattr(self, "_loop_visual_timer"):
            self._loop_visual_timer.stop()

        # Crear timer si no existeix
        if not hasattr(self, "_loop_visual_timer"):
            self._loop_visual_timer = QTimer(self)
            self._loop_visual_timer.timeout.connect(self._animate_loop_visual)
            self._loop_visual_phase = 0

        # Activar estat inicial
        self._loop_visual_active = True
        self._loop_visual_phase = 0
        self._animate_loop_visual()  # Primera animació immediata

        # Durada: 15 segons
        self._loop_visual_timer.start(300)  # 300ms per frame
        QTimer.singleShot(15000, self._stop_loop_visual_mode)  # 15 segons

    def _animate_loop_visual(self):
        """Anima els efectes visuals del LOOP mode."""
        self._loop_visual_phase = (self._loop_visual_phase + 1) % 8  # 8 fases

        # Color base per als decks (canvia ràpid)
        base_color = self._loop_visual_phase % 4  # 0-3: cicle ràpid

        # Colors MÉS INTENSOS i VISIBLES (opacitat 0.8-0.9)
        colors_a = [
            "rgba(0, 120, 212, 0.85)",  # Blau molt intens
            "rgba(0, 200, 83, 0.85)",  # Verd molt intens
            "rgba(255, 87, 34, 0.85)",  # Taronja molt intens
            "rgba(156, 39, 176, 0.85)",  # Lila molt intens
        ]

        colors_b = [
            "rgba(255, 87, 34, 0.85)",  # Taronja molt intens
            "rgba(156, 39, 176, 0.85)",  # Lila molt intens
            "rgba(0, 120, 212, 0.85)",  # Blau molt intens
            "rgba(0, 200, 83, 0.85)",  # Verd molt intens
        ]

        # Aplicar colors als decks - gradient més pronunciat
        try:
            self.deck_a.setStyleSheet(f"""
                QWidget {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 {colors_a[base_color]}, 
                        stop:0.5 rgba(30, 30, 30, 0.95),
                        stop:1 rgba(10, 10, 10, 1));
                    border: 2px solid {colors_a[base_color].replace("0.85", "1")};
                    border-radius: 8px;
                }}
            """)
            self.deck_b.setStyleSheet(f"""
                QWidget {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 {colors_b[base_color]}, 
                        stop:0.5 rgba(30, 30, 30, 0.95),
                        stop:1 rgba(10, 10, 10, 1));
                    border: 2px solid {colors_b[base_color].replace("0.85", "1")};
                    border-radius: 8px;
                }}
            """)
        except:
            pass  # Si no hi ha decks, ignorar

    def _stop_loop_visual_mode(self):
        """Atura el mode visual LOOP."""
        if hasattr(self, "_loop_visual_timer"):
            self._loop_visual_timer.stop()

        self._loop_visual_active = False

        # Restaurar colors originals
        try:
            self.deck_a.setStyleSheet("background: transparent;")
            self.deck_b.setStyleSheet("background: transparent;")
        except:
            pass

        # Desactivar botó
        if hasattr(self, "btn_loop"):
            self.btn_loop.setChecked(False)
            self.btn_loop.setText("🔁 LOOP")
            self.btn_loop.setStyleSheet("""
                QPushButton {
                    background-color: #333; color: #888; font-weight: bold; font-size: 11px;
                    border-radius: 3px; border: 1px solid #444;
                }
            """)

        logger.info("LOOP Visual Mode: Finalitzat")

    def _on_skip_and_mix(self):
        """SKIP Y MEZCLAR SIGUIENTE YA - Fuerza transición.
        Si el deck destino ya tiene una canción (cargada manualmente desde Llista 2),
        la respeta y solo hace el crossfade. Si está vacío, carga la siguiente de la playlist."""
        if self._fade_timer.isActive():
            return

        from_deck = "A" if self.crossfader.value() < 0 else "B"
        to_deck = "B" if from_deck == "A" else "A"

        from_deck_obj = self.deck_a if from_deck == "A" else self.deck_b
        to_deck_obj = self.deck_b if from_deck == "A" else self.deck_a

        # Comprovar si el deck destí ja té una cançó carregada
        current_dest = (
            to_deck_obj.current_file if hasattr(to_deck_obj, "current_file") else None
        )

        if not current_dest:
            # Deck destí buit: intentar carregar la següent de la playlist
            if not self._playlist_tracks or self._playlist_index >= len(
                self._playlist_tracks
            ):
                logger.warning(
                    "[SKIP+MEZCLAR] No hay canción en deck destino ni en playlist"
                )
                return
            expected_idx = self._playlist_index - 1
            if expected_idx < 0 or expected_idx >= len(self._playlist_tracks):
                logger.warning("[SKIP+MEZCLAR] \u00cdndice de playlist fuera de rango")
                return
            expected_path = self._playlist_tracks[expected_idx]
            logger.info(
                f"[SKIP+MEZCLAR] Cargando en deck {to_deck}: {os.path.basename(expected_path)}"
            )
            try:
                to_deck_obj.load_file(expected_path, False)
            except Exception as e:
                logger.error(f"[SKIP+MEZCLAR] Error cargando: {e}")
                return
        else:
            logger.info(
                f"[SKIP+MEZCLAR] Deck {to_deck} ya tiene: {os.path.basename(current_dest)} - respectant c\u00e0rrega manual"
            )

        # Iniciar transici\u00f3 (el deck dest\u00ed ja est\u00e0 preparat)
        self._start_transition(from_deck, skip_load=True)

    def _on_start_automix(self):
        """Inicia el modo automix: carga canción 1 en Deck A (sonando) y canción 2 en Deck B (preparada)."""
        logger.info(
            f"[Automix] Iniciando automix con {self.playlist_widget.table.rowCount()} pistas"
        )

        self._playlist_tracks = []
        for row in range(self.playlist_widget.table.rowCount()):
            it = self.playlist_widget.table.item(row, 4)
            if it:
                p = it.data(Qt.ItemDataRole.UserRole)
                if p:
                    self._playlist_tracks.append(p)

        logger.info(
            f"[Automix] Playlist tracks: {[os.path.basename(p) for p in self._playlist_tracks[:5]]}"
        )

        if not self._playlist_tracks:
            logger.warning("[Automix] No hay pistas para automix")
            self.playlist_widget.btn_automix.setChecked(False)
            self.playlist_widget._update_automix_button_style(False)
            return

        self._automix_active = True
        self._playlist_index = 0
        self.crossfader.setValue(-100)
        self._deck_started["A"] = False
        self._deck_started["B"] = False

        # Deck A: primera canción (sonando) - quitar de la lista visual
        self.deck_a.load_file(self._playlist_tracks[0], True)
        self.playlist_widget.increment_play_count(self._playlist_tracks[0])
        self.playlist_widget.remove_top_track()
        self._playlist_index = 1
        self._deck_started["A"] = True
        logger.info(
            f"[Automix] Deck A cargado: {os.path.basename(self._playlist_tracks[0])} (started=True)"
        )

        # Deck B: segunda canción (preparada) - quitar de la lista visual
        if len(self._playlist_tracks) > 1:
            self.deck_b.load_file(self._playlist_tracks[1], False)
            self.playlist_widget.remove_top_track()
            self._playlist_index = 2
            logger.info(
                f"[Automix] Deck B preparado: {os.path.basename(self._playlist_tracks[1])} (started=False)"
            )
        else:
            logger.info("[Automix] Solo hay 1 canci\u00f3n, no se prepara Deck B")

    def _on_automix_toggled(self, active):
        """Maneja el toggle del botón LANZAR MIX."""
        if active:
            # Si ya hay canciones cargadas y sonando, reactivar sin interrumpir
            if self._playlist_tracks and self._playlist_index > 0:
                logger.info(
                    f"[Automix] Reactivando automix sin interrumpir canción actual (index={self._playlist_index})"
                )
                self._automix_active = True
                self._transition_in_progress = False

                # Asegurar que el deck que está sonando tiene started=True
                for deck_name, deck_obj in [("A", self.deck_a), ("B", self.deck_b)]:
                    if deck_obj.player.playbackState() != 0:
                        self._deck_started[deck_name] = True
                        logger.info(f"[Automix] Deck {deck_name} marcado como iniciado")
            else:
                # Primera activación
                self._on_start_automix()
        else:
            logger.info(
                "[Automix] Parando automix - se dejará terminar la canción actual"
            )
            self._automix_active = False

            if self._s_timer and self._s_timer.isActive():
                self._s_timer.stop()
            if self._fallback_timer and self._fallback_timer.isActive():
                self._fallback_timer.stop()

            self._transition_in_progress = False

    def _check_automix(self, pos, deck):
        """Nom\u00e9s comprova automix si est\u00e0 actiu. Evita logs innecessaris quan no s'usa."""
        if not self._automix_active:
            return  # Silenci: no cal log si automix no est\u00e0 actiu
        if self._transition_in_progress:
            return  # Silenci: transici\u00f3 en curs
        p = self.deck_a.player if deck == "A" else self.deck_b.player
        fade_cfg = (
            self.playlist_widget.spin_fade.value()
            if self.playlist_widget.spin_fade
            else -5
        )
        # Debug logging limitada a cada 2 segons
        if (
            not hasattr(self, "_last_log_time")
            or time.time() - self._last_log_time >= 2.0
        ):
            logger.debug(
                f"[Automix] Deck {deck} check: pos={pos}ms, duration={p.duration()}ms, state={p.playbackState()}, started={self._deck_started[deck]}, fade_cfg={fade_cfg}"
            )
            self._last_log_time = time.time()

        # Actualizar estado de deck iniciado
        if p.playbackState() != 0:  # Playing or paused
            if not self._deck_started[deck]:
                self._deck_started[deck] = True
                logger.info(
                    f"[Automix] Deck {deck} marcado como iniciado (playbackState != 0)"
                )

        if fade_cfg >= 0:
            rem = p.duration() - pos
            # Solo iniciamos si NO hay una ya activa
            if (
                p.duration() > 0
                and rem > 0
                and rem <= (fade_cfg * 1000)
                and not self._fade_timer.isActive()
            ):
                # Evitar transiciones duplicadas si el fader ya está en el destino
                if (deck == "A" and self.crossfader.value() < 90) or (
                    deck == "B" and self.crossfader.value() > -90
                ):
                    logger.info(
                        f"[Automix] Deck {deck} fade activado (fade_cfg={fade_cfg}s, rem={rem}ms)"
                    )
                    self._start_transition(deck)
        else:
            # Modo silencio: esperar a que la canción termine (playbackState == 0) y haya empezado antes
            duration = p.duration()
            if duration > 0:
                remaining = duration - pos
                # Si la reproducción se ha detenido Y el deck había empezado, iniciar silencio
                logger.debug(
                    f"[Automix] Deck {deck} silence check: playbackState={p.playbackState()}, deck_started={self._deck_started[deck]}, remaining={remaining}"
                )
                if p.playbackState() == 0 and self._deck_started[deck]:
                    logger.info(
                        f"[Automix] Deck {deck} detenido, iniciando silencio de {abs(fade_cfg)} segundos"
                    )
                    if self._s_timer is None or not self._s_timer.isActive():
                        self._silence_rem = abs(fade_cfg) * 1000
                        self._f_deck = deck
                        self._start_silence_timer()
                # Fallback: si estamos muy cerca del final (≤100ms) y aún está sonando, también iniciar silencio (por si no detecta stop)
                elif (
                    remaining <= 100
                    and p.playbackState() != 0
                    and self._deck_started[deck]
                ):
                    logger.info(
                        f"[Automix] Deck {deck} cerca del final ({remaining}ms), iniciando silencio"
                    )
                    if self._s_timer is None or not self._s_timer.isActive():
                        self._silence_rem = abs(fade_cfg) * 1000
                        self._f_deck = deck
                        self._start_silence_timer()

    def _on_deck_finished(self, deck):
        """Se llama cuando un deck termina de reproducir (requestNext)."""
        logger.info(
            f"[Automix] _on_deck_finished called for deck {deck}, automix_active={self._automix_active}"
        )
        if not self._automix_active:
            logger.info(
                "[Automix] automix no activo - sesión terminada, reseteando botón"
            )
            self._playlist_tracks = []
            self._playlist_index = 0
            if (
                hasattr(self.playlist_widget, "btn_automix")
                and self.playlist_widget.btn_automix
            ):
                self.playlist_widget.btn_automix.setChecked(False)
                self.playlist_widget._update_automix_button_style(False)
            return
        # Obtener configuración de fade/silencio
        fade_cfg = (
            self.playlist_widget.spin_fade.value()
            if self.playlist_widget.spin_fade
            else -5
        )
        logger.info(f"[Automix] Deck {deck} fade_cfg={fade_cfg}s")

        # Iniciar timer de fallback por si no se detecta transición
        self._start_fallback_timer(deck)

        # En modo silencio (fade_cfg < 0), dejar que _check_automix maneje el silencio
        if fade_cfg < 0:
            logger.info(
                f"[Automix] Deck {deck} requestNext ignorado (modo silencio={fade_cfg}s)"
            )
            return

        # Protección contra múltiples llamadas simultáneas
        if hasattr(self, "_transition_in_progress") and self._transition_in_progress:
            logger.debug(
                f"[Automix] Ignorando deck_finished({deck}) - transición ya en progreso"
            )
            return
        logger.info(
            f"[Automix] Deck {deck} terminó, iniciando transición (fade={fade_cfg}s)"
        )
        # Iniciar transición desde este deck (automix activo)
        self._start_transition(deck)

    def _start_silence_timer(self):
        logger.info(
            f"[Automix] _start_silence_timer called, _silence_rem={self._silence_rem}ms, _f_deck={self._f_deck}"
        )
        if self._s_timer is None:
            self._s_timer = QTimer()
            self._s_timer.setSingleShot(True)
            self._s_timer.timeout.connect(lambda: self._start_transition(self._f_deck))
        self._s_timer.start(self._silence_rem)

    def _start_fallback_timer(self, deck):
        """Inicia un timer de fallback por si no se detecta el fin de la canción."""
        if self._fallback_timer is None:
            self._fallback_timer = QTimer()
            self._fallback_timer.setSingleShot(True)
            self._fallback_timer.timeout.connect(
                lambda: self._fallback_transition(deck)
            )
        # Esperar 10 segundos después del requestNext
        self._fallback_timer.start(10000)
        logger.info(f"[Automix] Fallback timer iniciado para deck {deck} (10s)")

    def _fallback_transition(self, deck):
        """Transición forzada después de timeout."""
        if not self._automix_active:
            return
        if self._transition_in_progress:
            logger.debug("[Automix] Fallback ignorado - transición ya en progreso")
            return
        logger.warning(
            f"[Automix] Fallback activado para deck {deck} - forzando transición"
        )
        self._start_transition(deck)

    def _start_transition(self, from_deck, skip_load=False):
        """Transición de un deck a otro usando el índice de playlist.
        from_deck: deck que está sonando actualmente
        skip_load: si True, asume que el deck destino ya está cargado y omite la carga.
        Después del crossfade, se carga la subsiguiente canción en el deck libre (si no se skipa)."""
        if self._fallback_timer is not None and self._fallback_timer.isActive():
            self._fallback_timer.stop()
            logger.debug("[Automix] Fallback timer cancelado")
        if self._transition_in_progress:
            logger.debug(
                f"[Automix] Ignorando _start_transition({from_deck}) - ya en progreso"
            )
            return
        self._transition_in_progress = True
        self._manual_crossfade = False
        logger.info(
            f"[Automix] _start_transition desde {from_deck}, playlist_index={self._playlist_index}, skip_load={skip_load}"
        )

        to_deck = "B" if from_deck == "A" else "A"
        to_deck_obj = self.deck_b if from_deck == "A" else self.deck_a
        from_deck_obj = self.deck_a if from_deck == "A" else self.deck_b

        # Preparar deck destino (para automix normal, no skip)
        if not skip_load:
            # Verificar que haya pistas disponibles
            if self._playlist_index >= len(self._playlist_tracks):
                logger.info("[Automix] No hay más canciones en la playlist")
                self._automix_active = False
                self._transition_in_progress = False
                if (
                    hasattr(self.playlist_widget, "btn_automix")
                    and self.playlist_widget.btn_automix
                ):
                    self.playlist_widget.btn_automix.setChecked(False)
                    self.playlist_widget._update_automix_button_style(False)
                return

            # Asegurar que el deck destino tenga una pista cargada.
            # Normalmente ya tiene la pista cargada desde la transición anterior (índice _playlist_index - 1).
            if not to_deck_obj.current_file:
                expected_idx = self._playlist_index - 1
                if expected_idx >= 0 and expected_idx < len(self._playlist_tracks):
                    expected_path = self._playlist_tracks[expected_idx]
                    try:
                        to_deck_obj.load_file(expected_path, False)
                        logger.info(
                            f"[Automix] Cargada en {to_deck} (pista esperada): {os.path.basename(expected_path)}"
                        )
                    except Exception as e:
                        logger.error(
                            f"[Automix] Error cargando pista esperada en deck destino: {e}"
                        )
                        return
                else:
                    logger.warning(
                        f"[Automix] No se puede cargar deck destino, índice fuera de rango: {expected_idx}"
                    )
                    return

            # Iniciar reproducción en el deck destino si no está sonando
            if not self._deck_started.get(to_deck, False):
                to_deck_obj.play()
                if to_deck_obj.deck and hasattr(to_deck_obj.deck, "is_playing"):
                    logger.info(
                        f"[Automix] Deck {to_deck} is_playing después de play(): {to_deck_obj.deck.is_playing}"
                    )
                self._deck_started[to_deck] = True
        else:
            logger.info(
                "[SKIP+MEZCLAR] Deck destino ya preparado, omitiendo carga propia"
            )
            # Si el deck destino tiene canción cargada pero no está sonando, iniciar reproducción
            if to_deck_obj.current_file and not self._deck_started.get(to_deck, False):
                logger.info(f"[SKIP+MEZCLAR] Iniciando reproducción en deck {to_deck}")
                to_deck_obj.play()
                if to_deck_obj.deck and hasattr(to_deck_obj.deck, "is_playing"):
                    logger.info(
                        f"[SKIP+MEZCLAR] Deck {to_deck} is_playing después de play(): {to_deck_obj.deck.is_playing}"
                    )
                self._deck_started[to_deck] = True

        # Incrementar play count de la canción que estaba sonando
        current_file = from_deck_obj.current_file
        if current_file:
            self.playlist_widget.increment_play_count(current_file)

        # Calcular tiempo de fade basado en self.playlist_widget.spin_fade
        fade_val = (
            self.playlist_widget.spin_fade.value()
            if self.playlist_widget.spin_fade
            else -5
        )
        fade_secs = float(abs(fade_val))
        fade_secs = max(fade_secs, 0.5)
        self._fade_target_val = 100.0 if from_deck == "A" else -100.0
        self._fade_current_val = float(self.crossfader.value())
        self._fade_step = 200.0 / (fade_secs * 50.0)
        self._fade_timer.start(20)
        # Mostrar inmediatamente "CAMBIANDO..." al iniciar transición
        self.lbl_transition_timer.setText("CAMBIANDO...")
        self.lbl_transition_timer.setStyleSheet(
            "color: #4dabf7; font-size: 10px; font-weight: bold;"
        )

    def _update_transition_timer(self):
        """Actualiza el display del temporizador de transición visible"""
        if self._fade_timer.isActive():
            remaining_ms = self._fade_timer.remainingTime()
            if remaining_ms > 0:
                remaining_sec = remaining_ms // 1000
                # Mostrar cuenta regresiva solo cuando quedan 5 segundos o menos
                if remaining_sec <= 5:
                    self.lbl_transition_timer.setText(f"⏱ {remaining_sec:02d}")
                    # Color warn cuando <2s
                    if remaining_sec < 2:
                        self.lbl_transition_timer.setStyleSheet(
                            "color: #ff6b6b; font-size: 10px; font-weight: bold;"
                        )
                    else:
                        self.lbl_transition_timer.setStyleSheet(
                            "color: #ffd93d; font-size: 10px; font-weight: bold;"
                        )
                else:
                    self.lbl_transition_timer.setText("⏱ --")
                    self.lbl_transition_timer.setStyleSheet(
                        "color: #aaa; font-size: 10px; font-weight: bold;"
                    )
            else:
                self.lbl_transition_timer.setText("CAMBIANDO...")
                self.lbl_transition_timer.setStyleSheet(
                    "color: #4dabf7; font-size: 10px; font-weight: bold;"
                )
        else:
            self.lbl_transition_timer.setText("⏱ --")
            self.lbl_transition_timer.setStyleSheet(
                "color: #aaa; font-size: 10px; font-weight: bold;"
            )

    def _handle_transition_logic(self):
        if self._fade_target_val > self._fade_current_val:
            self._fade_current_val += self._fade_step
            self._fade_current_val = min(self._fade_target_val, self._fade_current_val)
        else:
            self._fade_current_val -= self._fade_step
            self._fade_current_val = max(self._fade_target_val, self._fade_current_val)

        # Mover crossfader - esto dispara _on_crossfader_changed que aplica volúmenes
        self.crossfader.setValue(int(self._fade_current_val))

        if self._fade_current_val == self._fade_target_val:
            self._fade_timer.stop()
            # Resetear label de transición
            self.lbl_transition_timer.setText("⏱ --")
            self.lbl_transition_timer.setStyleSheet(
                "color: #aaa; font-size: 10px; font-weight: bold;"
            )
            if not getattr(self, "_manual_crossfade", False):
                from_deck_obj = (
                    self.deck_a if self._fade_target_val == 100 else self.deck_b
                )
                from_deck_obj.player.stop()
                logger.info(f"[Automix] Transición: parado {from_deck_obj.name}")
                # Marcar el deck com a no iniciat per que no es detecti silenci de nou
                deck_letter = from_deck_obj.name[-1]
                self._deck_started[deck_letter] = False
                logger.info(f"[Automix] Deck {deck_letter} marcat com a no iniciat")
                # Cancel·lar el silenci timer d'aquest deck per evitar bucles
                if (
                    hasattr(self, "_s_timer")
                    and self._s_timer
                    and self._s_timer.isActive()
                    and self._f_deck == deck_letter
                ):
                    self._s_timer.stop()
                    logger.info(
                        f"[Automix] Silenci timer cancel·lat per {from_deck_obj.name}"
                    )

                # Cargar la siguiente canción en el deck liberado y actualizar la playlist
                if self._automix_active and self._playlist_index < len(
                    self._playlist_tracks
                ):
                    try:
                        next_path = self._playlist_tracks[self._playlist_index]
                        from_deck_obj.load_file(next_path, False)
                        self.playlist_widget.remove_top_track()
                        self._playlist_index += 1
                        logger.info(
                            f"[Automix] Cargada siguiente en deck liberado {from_deck_obj.name}: {os.path.basename(next_path)}"
                        )
                    except Exception as e:
                        logger.error(
                            f"[Automix] Error cargando siguiente en deck liberado: {e}"
                        )
                else:
                    # No hay más canciones: desactivar automix
                    logger.info("[Automix] No hay más canciones en la playlist")
                    self._automix_active = False
                    if (
                        hasattr(self.playlist_widget, "btn_automix")
                        and self.playlist_widget.btn_automix
                    ):
                        self.playlist_widget.btn_automix.setChecked(False)
                        self.playlist_widget._update_automix_button_style(False)

            self._manual_crossfade = False
            self._transition_in_progress = False
            logger.info("[Automix] Transición completada")
