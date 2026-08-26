import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


class DuplicateDialog(QDialog):
    fileDeleteRequested = Signal(str)  # Señal para liberar archivo antes de borrar

    def __init__(self, analyzed_files: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔍 Detectar Duplicados")
        self.setMinimumSize(900, 500)
        self.analyzed_files = analyzed_files
        self.duplicates = []
        self.current_playing_row = -1
        self._setup_ui()

        # Ejecutar búsqueda automáticamente al abrir
        self._scan_duplicates()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Selector de modo
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Modo de detección:"))
        self.cb_mode = QComboBox()
        self.cb_mode.addItems(
            [
                "Contenido idéntico (SHA256)",
                "Mismo nombre de archivo",
                "Mismo Título + Artista",
                "Misma duración",
                "Mismo tamaño + duración",
            ]
        )
        self.cb_mode.currentIndexChanged.connect(self._scan_duplicates)
        mode_layout.addWidget(self.cb_mode)

        self.btn_scan = QPushButton("Buscar Duplicados")
        self.btn_scan.clicked.connect(self._scan_duplicates)
        mode_layout.addWidget(self.btn_scan)
        mode_layout.addStretch()

        layout.addLayout(mode_layout)

        # Tabla de resultados
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels(
            [
                "▶",
                "Grupo",
                "Archivo",
                "Duración",
                "Bitrate",
                "Tamaño",
                "Carpeta",
                "Calidad",
                "Eliminar",
            ]
        )
        # Columnas con ancho fijo
        self.table.setColumnWidth(0, 35)  # Play
        self.table.setColumnWidth(1, 70)  # Grupo
        self.table.setColumnWidth(2, 200)  # Archivo
        self.table.setColumnWidth(3, 60)  # Duración
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Interactive
        )  # Archivo
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.doubleClicked.connect(self._on_double_click_row)
        layout.addWidget(self.table)

        # Botones
        btn_layout = QHBoxLayout()

        self.btn_auto_select = QPushButton("🎯 Seleccionar Peores")
        self.btn_auto_select.setStyleSheet(
            "background-color: #ff9800; color: white; padding: 8px;"
        )
        self.btn_auto_select.clicked.connect(self._auto_select_worst)
        btn_layout.addWidget(self.btn_auto_select)

        self.btn_delete = QPushButton("🗑 Eliminar Seleccionado")
        self.btn_delete.setStyleSheet(
            "background-color: #d32f2f; color: white; padding: 8px;"
        )
        self.btn_delete.clicked.connect(self._delete_selected)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_delete)

        self.btn_close = QPushButton("Cerrar")
        self.btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_close)

        layout.addLayout(btn_layout)

        # Info
        self.lbl_info = QLabel("")
        layout.addWidget(self.lbl_info)

    def _calculate_quality_score(self, f: dict, root_folder: str = "") -> dict:
        """
        Calcula una puntuación de calidad para cada archivo.

        Criterios (en orden de prioridad):
        1. bitrate_real (FFT) - el más importante para detectar fakes
        2. Si es fake (bitrate_real < bitrate), penalización
        3. Tamaño más pequeño (mejor compresión)
        4. En carpeta raíz (más accesible)
        """
        bitrate = f.get("bitrate") or 0
        bitrate_real = f.get("bitrate_real") or 0
        size_mb = f.get("size_mb") or 0

        score = 0
        reasons = []

        # 1. Usar bitrate real si está disponible, si no el del header
        effective_br = bitrate_real if bitrate_real else bitrate

        if bitrate_real and bitrate_real > 0:
            # tenemos análisis espectral
            if bitrate_real < bitrate:
                # ES FAKE! Penalización fuerte
                score += bitrate_real * 0.8  # Usamos el real pero con penalización
                reasons.append(f"⚠️ FAKE: {bitrate}->{bitrate_real} kbps")
            else:
                score += bitrate_real
                if bitrate != bitrate_real:
                    reasons.append(f"✓ Verificado: {bitrate_real} kbps")
                else:
                    reasons.append(f"✓ {bitrate_real} kbps (OK)")
        else:
            # Sin análisis FFT, usar header
            score += bitrate
            reasons.append(f"? {bitrate} kbps (header)")

        # 2. Tamaño: archivos más pequeños penalizados ligeramente
        # (pero no demasiado, para no penalizar grabaciones cortas)
        if size_mb > 0:
            # Normalizar: menor tamaño = mejor score relativo
            # Pero solo si la duración es similar
            duration = f.get("duration") or 0
            if duration > 60:  # Solo para canciones > 1 min
                # MB por minuto
                mb_per_min = size_mb / (duration / 60)
                if mb_per_min < 0.5:  # Muy comprimido
                    score *= 0.9
                    reasons.append("⚠️ Muy comprimido")
                elif mb_per_min > 2.5:  # Muy grande
                    score *= 0.95
                    reasons.append("⚠️ Archivo grande")

        # 3. Carpeta raíz vs subcarpeta
        folder = f.get("folder", "")
        if root_folder and folder == root_folder:
            score *= 1.05  # Ligera preferencia por carpeta raíz
            reasons.append("📁 Carpeta raíz")

        return {
            "score": score,
            "reasons": reasons,
            "is_fake": bitrate_real > 0 and bitrate_real < bitrate,
            "effective_bitrate": effective_br,
        }

    def _scan_duplicates(self):
        mode = self.cb_mode.currentIndex()
        self.duplicates = []

        # Normalizar todas las rutas para evitar duplicados por diferencia de slash
        normalized_files = {}
        for fp, mf in self.analyzed_files.items():
            # Normalizar ruta: usar os.path.normpath para convertir / a \ en Windows
            # Luego usar forward slashes consistente
            norm_fp = os.path.normpath(fp).replace("\\", "/")
            normalized_files[norm_fp] = mf

        self.analyzed_files = normalized_files

        # Obtener carpeta raíz para comparaciones
        root_folder = ""
        if self.analyzed_files:
            first_fp = next(iter(self.analyzed_files.keys()))
            root_folder = os.path.dirname(first_fp)

        # Agrupar archivos por criterio
        groups = {}

        for fp, mf in self.analyzed_files.items():
            if not os.path.exists(fp):
                continue

            # Determinar si es MusicFile o dict
            is_dict = isinstance(mf, dict)

            # Obtener valores con seguridad
            duration_val = 0
            bitrate_val = 0
            bitrate_real_val = 0
            title = ""
            artist = ""
            sha256_val = ""

            if is_dict:
                # Es un diccionario (de la base de datos)
                duration_val = mf.get("duration", 0) or 0
                bitrate_val = mf.get("bitrate", 0) or 0
                bitrate_real_val = mf.get("bitrate_real", 0) or 0
                title = mf.get("title", "") or ""
                artist = mf.get("artist", "") or ""
                sha256_val = mf.get("sha256", "") or ""
            else:
                # Es un objeto MusicFile
                tech = mf.technical if mf else None
                meta = mf.metadata if mf else None

                if tech:
                    duration_val = getattr(tech, "duration", 0) or 0
                    bitrate_val = getattr(tech, "bitrate", 0) or 0
                    bitrate_real_val = getattr(tech, "bitrate_real", 0) or 0

                if meta:
                    title = getattr(meta, "title", "") or ""
                    artist = getattr(meta, "artist", "") or ""

                sha256_val = getattr(mf, "sha256", "") or ""

            # Obtener tamaño del archivo
            try:
                file_size = os.path.getsize(fp)
            except Exception:
                file_size = 0

            key = ""
            if mode == 0:  # SHA256
                key = sha256_val if sha256_val else fp
            elif mode == 1:  # Nombre de archivo
                key = os.path.basename(fp)
            elif mode == 2:  # Título + Artista
                key = f"{title} | {artist}" if title or artist else fp
            elif mode == 3:  # Duración
                key = str(int(duration_val)) if duration_val else "0"
            elif mode == 4:  # Tamaño + duración
                key = str(file_size)

            if key:
                if key not in groups:
                    groups[key] = []
                groups[key].append(
                    {
                        "path": fp,
                        "filename": os.path.basename(fp),
                        "folder": os.path.dirname(fp),
                        "duration": duration_val,
                        "bitrate": bitrate_val,
                        "bitrate_real": bitrate_real_val,
                        "size_mb": (file_size / (1024 * 1024)),
                    }
                )

        # Filtrar grupos con más de 1 archivo
        for key, files in groups.items():
            if len(files) > 1:
                # Para modo tamaño + duración, aplicar lógica inteligente
                if mode == 4:  # Modo tamaño + duración
                    # Agrupar por duración dentro del mismo tamaño
                    duration_groups = {}
                    for f in files:
                        dur_key = str(int(f.get("duration") or 0))
                        if dur_key not in duration_groups:
                            duration_groups[dur_key] = []
                        duration_groups[dur_key].append(f)

                    # Añadir cada grupo de duración
                    for dur_key, same_duration in duration_groups.items():
                        if len(same_duration) > 1:
                            # Ordenar por calidad mejorada
                            same_duration.sort(
                                key=lambda x: self._calculate_quality_score(
                                    x, root_folder
                                )["score"],
                                reverse=True,
                            )
                            self.duplicates.append(
                                {"key": f"{key} ({dur_key}s)", "files": same_duration}
                            )
                else:
                    # Ordenar por calidad mejorada
                    files.sort(
                        key=lambda x: self._calculate_quality_score(x, root_folder)[
                            "score"
                        ],
                        reverse=True,
                    )
                    self.duplicates.append({"key": key, "files": files})

        self._display_results()

    def _display_results(self):
        self.table.setRowCount(0)
        total_dupes = 0

        # Color más claro para el mejor
        best_bg = QColor(0, 100, 0, 60)  # Verde transparente

        for group_idx, group in enumerate(self.duplicates):
            files = group["files"]
            total_dupes += len(files) - 1

            for file_idx, f in enumerate(files):
                row = self.table.rowCount()
                self.table.insertRow(row)

                # Preview botón al principio
                btn = QPushButton("▶")
                btn.setFixedSize(30, 20)
                current_row = row
                btn.clicked.connect(
                    lambda checked, path=f["path"], r=current_row: self._preview_file(
                        path, r
                    )
                )
                self.table.setCellWidget(row, 0, btn)

                # Grupo
                if file_idx == 0:
                    self.table.setItem(
                        row, 1, QTableWidgetItem(f"Grupo {group_idx + 1}")
                    )
                else:
                    self.table.setItem(row, 1, QTableWidgetItem(""))

                # Archivo
                self.table.setItem(row, 2, QTableWidgetItem(f["filename"]))
                self.table.item(row, 2).setData(Qt.ItemDataRole.UserRole, f["path"])

                # Duración
                dur = f.get("duration")
                if dur and dur > 0:
                    mins = int(dur // 60)
                    secs = int(dur % 60)
                    dur_str = f"{mins:02d}:{secs:02d}"
                else:
                    dur_str = "-"
                self.table.setItem(row, 3, QTableWidgetItem(dur_str))

                # Bitrate (mostrar real con detección de fake)
                br = f.get("bitrate", 0)
                br_real = f.get("bitrate_real", 0)
                if br_real and br_real != br:
                    br_str = f"{br}->{br_real} kbps ⚠️"
                else:
                    br_str = f"{br} kbps"
                self.table.setItem(row, 4, QTableWidgetItem(br_str))

                # Tamaño
                size_mb = f.get("size_mb") or 0
                self.table.setItem(
                    row,
                    5,
                    QTableWidgetItem(f"{size_mb:.1f} MB" if size_mb > 0 else "-"),
                )

                # Carpeta
                folder = f.get("folder", "")
                self.table.setItem(row, 6, QTableWidgetItem(folder))

                # Calidad con razones detalladas
                is_best = file_idx == 0
                quality_info = self._calculate_quality_score(f)

                if is_best:
                    # Mostrar razones para el mejor
                    reasons_str = " | ".join(
                        quality_info["reasons"][:2]
                    )  # Max 2 razones
                    quality = f"✓ {quality_info['effective_bitrate']} kbps"
                else:
                    quality = f"{quality_info['effective_bitrate']} kbps"

                item_qual = QTableWidgetItem(quality)
                item_qual.setToolTip(
                    " | ".join(quality_info["reasons"])
                )  # Tooltip con todas las razones
                item_qual.setForeground(
                    QColor("#22aa22") if is_best else QColor("#dd3333")
                )
                self.table.setItem(row, 7, item_qual)

                # Checkbox
                chk = QTableWidgetItem()
                chk.setFlags(
                    Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled
                )
                chk.setCheckState(Qt.CheckState.Unchecked)
                self.table.setItem(row, 8, chk)

                # Resaltar el mejor con color más claro
                if is_best:
                    for c in range(9):
                        if self.table.item(row, c):
                            self.table.item(row, c).setBackground(best_bg)

        self.lbl_info.setText(
            f"Se encontraron {len(self.duplicates)} grupos con {total_dupes} archivos duplicados"
        )

    def _preview_file(self, filepath, row):
        player = self.parent().player_widget

        # Si ya está reproduciendo este archivo, parar
        if self.current_playing_row == row:
            player.stop()
            self._clear_playing_indicator(row)
            self.current_playing_row = -1
            return

        # Limpiar indicador anterior
        if self.current_playing_row >= 0:
            self._clear_playing_indicator(self.current_playing_row)

        # Reproducir nuevo archivo
        player.load_file(filepath, auto_play=True)

        # Marcar esta fila como reproduciendo
        self.current_playing_row = row
        playing_bg = QColor(0, 100, 200, 60)  # Azul transparente
        for c in range(9):
            if self.table.item(row, c):
                self.table.item(row, c).setBackground(playing_bg)

    def _clear_playing_indicator(self, row):
        if row < 0:
            return
        # Quitar el indicador azul y restaurar el color original si es el "mejor"
        item7 = self.table.item(row, 7)
        is_best = (
            row < self.table.rowCount()
            and item7 is not None
            and item7.text() == "✓ MEJOR"
        )
        bg = QColor(0, 100, 0, 60) if is_best else QColor(255, 255, 255)
        for c in range(9):
            if self.table.item(row, c):
                self.table.item(row, c).setBackground(bg)

    def _auto_select_worst(self):
        """Selecciona automáticamente los archivos de menor calidad en cada grupo de duplicados."""
        # Agrupar filas por grupo usando el texto de la columna Grupo
        # El patrón es "Grupo N" o vacío para la primera fila de cada grupo
        current_group = None
        group_rows = []
        groups = {}

        for row in range(self.table.rowCount()):
            group_item = self.table.item(row, 1)  # Columna Grupo
            group_text = group_item.text() if group_item else ""

            # Si tiene texto "Grupo N", es inicio de nuevo grupo
            if group_text.startswith("Grupo "):
                if current_group and group_rows:
                    groups[current_group] = group_rows
                current_group = group_text
                group_rows = []

            # Obtener score de calidad (columna 7)
            score_item = self.table.item(row, 7)
            score_text = score_item.text() if score_item else "0"

            # Extraer el número de kbps del texto (ej: "✓ 320 kbps" o "128 kbps")
            # El formato es: [simbolo] [numero] kbps
            import re

            match = re.search(r"(\d+)", score_text)
            if match:
                score = float(match.group(1))
            else:
                score = 0

            group_rows.append((row, score))

        # Añadir el último grupo
        if current_group and group_rows:
            groups[current_group] = group_rows

        # Depuración
        import logging

        logging.getLogger(__name__).debug(f"Grupos encontrados: {len(groups)}")

        # Seleccionar el de menor score en cada grupo (excepto si solo hay 1)
        selected_count = 0
        for group_id, items in groups.items():
            if len(items) > 1:
                # Ordenar por score (menor primero)
                items.sort(key=lambda x: x[1])
                # Seleccionar el primero (peor calidad)
                worst_row = items[0][0]
                chk = self.table.item(worst_row, 8)
                if chk:
                    chk.setCheckState(Qt.CheckState.Checked)
                    selected_count += 1

        if selected_count > 0:
            QMessageBox.information(
                self,
                "Selección Automática",
                f"Se han seleccionado {selected_count} archivos de menor calidad.\n\n"
                "Revisa la selección y haz clic en 'Eliminar Seleccionado' para borrarlos.",
            )
        else:
            QMessageBox.information(
                self,
                "Sin Selección",
                "No se encontraron grupos con múltiples archivos para seleccionar.",
            )

    def _delete_selected(self):
        # Recoger archivos a eliminar (columna 8 = Eliminar)
        to_delete = []
        for row in range(self.table.rowCount()):
            chk = self.table.item(row, 8)
            if chk and chk.checkState() == Qt.CheckState.Checked:
                path_item = self.table.item(row, 2)
                if path_item:
                    path = path_item.data(Qt.ItemDataRole.UserRole)
                    if path:
                        to_delete.append(path)

        if not to_delete:
            QMessageBox.information(
                self,
                "Información",
                "Selecciona los archivos a eliminar marcando la columna 'Eliminar'",
            )
            return

        reply = QMessageBox.question(
            self,
            "Confirmar eliminación",
            f"¿Eliminar {len(to_delete)} archivos definitivamente?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            deleted = 0
            deleted_files = []  # Lista de archivos eliminados para el log
            failed = []
            for fp in to_delete:
                # Emitir señal para liberar el archivo si está en uso
                self.fileDeleteRequested.emit(fp)

                import time

                max_attempts = 3
                for attempt in range(max_attempts):
                    try:
                        os.remove(fp)
                        deleted += 1
                        deleted_files.append(fp)
                        break  # Éxito
                    except PermissionError:
                        if attempt < max_attempts - 1:
                            time.sleep(0.5)
                    except Exception as e:
                        failed.append(f"{fp}: {e}")
                        break

            # Generar archivo de log con los eliminados
            if deleted_files:
                import datetime

                from PySide6.QtWidgets import QFileDialog

                # Nombre del archivo con fecha/hora
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                default_name = f"eliminados_{timestamp}.txt"

                # Pedir ubicación para guardar
                save_path, _ = QFileDialog.getSaveFileName(
                    self,
                    "Guardar lista de eliminados",
                    default_name,
                    "Text files (*.txt)",
                )

                if save_path:
                    try:
                        with open(save_path, "w", encoding="utf-8") as f:
                            f.write("JM-MusicAnalyzer - Archivos Eliminados\n")
                            f.write(
                                f"Fecha: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                            )
                            f.write(f"Total eliminados: {deleted}\n")
                            f.write("=" * 60 + "\n\n")
                            for i, filepath in enumerate(deleted_files, 1):
                                f.write(f"{i}. {os.path.basename(filepath)}\n")
                                f.write(f"   Ruta: {filepath}\n\n")
                        QMessageBox.information(
                            self,
                            "Éxito",
                            f"Se eliminaron {deleted} archivos\n\n"
                            f"Lista guardada en:\n{save_path}",
                        )
                    except Exception as e:
                        QMessageBox.warning(
                            self,
                            "Error guardando log",
                            f"Se eliminaron {deleted} archivos pero no se pudo guardar la lista:\n{e}",
                        )
                else:
                    QMessageBox.information(
                        self, "Éxito", f"Se eliminaron {deleted} archivos"
                    )

                self._scan_duplicates()  # Refresh

            if failed:
                QMessageBox.warning(
                    self,
                    "Errores",
                    f"No se pudieron eliminar {len(failed)} archivos:\n\n"
                    + "\n".join(failed[:5]),
                )

    def _on_double_click_row(self, index):
        """Abre la canción seleccionada en la ventana principal para editar."""
        row = index.row()
        # Obtener la ruta del archivo (columna 2 = Archivo)
        item = self.table.item(row, 2)
        if not item:
            return

        filepath = item.data(Qt.ItemDataRole.UserRole)
        if not filepath:
            return

        # Cerrar este diálogo
        self.accept()

        # Abrir/cargar la canción en la ventana principal
        main_window = self.parent()
        if main_window and hasattr(main_window, "_on_file_selected"):
            # Cargar la canción en el reproductor principal
            main_window._on_file_selected(filepath)

            # Si la ventana principal está oculta, mostrarla
            if not main_window.isVisible():
                main_window.show()

            # Traer al frente
            main_window.raise_()
            main_window.activateWindow()
        else:
            # Si no tenemos acceso a la ventana principal, simplemente mostrar un mensaje
            QMessageBox.information(
                self,
                "Editar canción",
                f"Para editar los metadatos:\n\n{filepath}\n\n"
                "Abre la canción desde la ventana principal del programa.",
            )
