import os
import sqlite3

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


class FavoritesManagerDialog(QDialog):
    """
    Diálogo para gestionar carpetas favorites.
    Permite escanear, renombrar, eliminar y ver estadísticas.
    """

    def eventFilter(self, obj, event):
        """Filtra eventos de teclado."""
        if obj == self.table and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
                self._on_enter_pressed()
                return True
        return super().eventFilter(obj, event)

    def _on_enter_pressed(self):
        """Maneja Enter en la tabla - escanea la selección."""
        row = self.table.currentRow()
        if row >= 0:
            path_item = self.table.item(row, 0)
            if path_item:
                fav_path = path_item.data(Qt.ItemDataRole.UserRole)
                if fav_path:
                    self._scan_folder_no_close(fav_path)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestionar Favoritos")
        self.setMinimumSize(800, 400)
        self.setWindowIcon(
            QApplication.style().standardIcon(
                QApplication.style().StandardPixmap.SP_DirIcon
            )
        )

        from services.bookmarks_manager import BookmarksManager

        self.bookmarks_manager = BookmarksManager()

        self.scan_subfolders = True  # Por defecto: incluir subcarpetas
        self._scanning_fav_path = None
        self._scanning_main_window = None
        self._setup_ui()
        self._load_favorites()

        # Timer para refrescar automáticamente después del escaneo
        from PySide6.QtCore import QTimer

        self.refresh_timer = QTimer()
        self.refresh_timer.setInterval(2000)  # 2 segundos
        self.refresh_timer.timeout.connect(self._on_refresh_timer)

    @staticmethod
    def _normalize_path(p):
        """
        Normaliza un path para comparación.
        Usa la función centralizada de database_manager.
        """
        from utils.paths import normalize_path

        if not p:
            return p
        return normalize_path(p).lower()

    def _on_refresh_timer(self):
        """Manejador del timer de refresco: verifica si el escaneo terminó y actualiza."""
        import logging

        logger = logging.getLogger(__name__)

        # Verificar si hay un escaneo en curso
        if self._scanning_main_window and hasattr(self._scanning_main_window, "worker"):
            worker = self._scanning_main_window.worker
            if worker and worker.isRunning():
                logger.info(
                    "_on_refresh_timer: escaneo aún en curso, esperando... (worker.isRunning=True)"
                )
                # El timer seguirá activo, no hacemos nada ahora
                return
            logger.info(
                "_on_refresh_timer: worker existe pero no está corriendo (isRunning=False)"
            )

        # Si llegamos aquí, el escaneo terminó o no hay escaneo activo
        logger.info(
            "_on_refresh_timer: escaneo terminado o no activo, recargando favoritos"
        )
        logger.info(
            f"_on_refresh_timer: _scanning_fav_path={self._scanning_fav_path}, _scanning_main_window={self._scanning_main_window}"
        )
        self.refresh_timer.stop()
        self._load_favorites()

        # Limpiar referencias
        self._scanning_fav_path = None
        self._scanning_main_window = None

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Info label
        self.lbl_info = QLabel(
            "💡 Doble clic o Enter = Escanear | Click derecho = Menú"
        )
        self.lbl_info.setStyleSheet("color: #666; font-size: 11px; padding: 5px;")
        layout.addWidget(self.lbl_info)

        # Checkbox for subfolders
        self.chk_subfolders = QCheckBox("Incluir subcarpetas al escanear")
        self.chk_subfolders.setChecked(self.scan_subfolders)
        self.chk_subfolders.stateChanged.connect(self._on_subfolders_changed)
        layout.addWidget(self.chk_subfolders)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(
            ["Carpeta", "Archivos", "Último escaneo", "Path"]
        )
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Interactive
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Fixed
        )
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Fixed
        )
        self.table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Stretch
        )

        self.table.setColumnWidth(0, 150)
        self.table.setColumnWidth(1, 80)
        self.table.setColumnWidth(2, 140)

        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        # Tecla Enter para escanear
        self.table.installEventFilter(self)

        # Doble clic para escanear
        self.table.itemDoubleClicked.connect(self._on_item_double_clicked)

        layout.addWidget(self.table)

        # Buttons
        btn_layout = QHBoxLayout()

        self.btn_scan = QPushButton("🔍 Escanear")
        self.btn_scan.clicked.connect(self._scan_selected)
        btn_layout.addWidget(self.btn_scan)

        self.btn_refresh = QPushButton("🔄 Actualizar")
        self.btn_refresh.clicked.connect(self._load_favorites)
        btn_layout.addWidget(self.btn_refresh)

        btn_layout.addSpacing(10)

        self.btn_info = QPushButton("ℹ️ Info")
        self.btn_info.clicked.connect(self._on_info_clicked)
        self.btn_info.setToolTip("Ver propiedades de la carpeta seleccionada")
        btn_layout.addWidget(self.btn_info)

        self.btn_open = QPushButton("📂 Abrir")
        self.btn_open.clicked.connect(self._on_open_clicked)
        self.btn_open.setToolTip("Abrir carpeta en Explorador")
        btn_layout.addWidget(self.btn_open)

        self.btn_delete = QPushButton("🗑️ Eliminar")
        self.btn_delete.clicked.connect(self._on_delete_clicked)
        self.btn_delete.setToolTip("Eliminar de favoritos")
        btn_layout.addWidget(self.btn_delete)

        btn_layout.addStretch()

        self.btn_close = QPushButton("Cerrar")
        self.btn_close.clicked.connect(self.close)
        btn_layout.addWidget(self.btn_close)

        layout.addLayout(btn_layout)

    def _load_favorites(self):
        """Carga la lista de favoritos y sus estadísticas usando SQL directo."""
        import logging

        logger = logging.getLogger(__name__)

        from services.db import get_db
        from utils.paths import normalize_path

        db = get_db()

        favorites = self.bookmarks_manager.load_bookmarks()
        logger.info(f"_load_favorites: {len(favorites)} favoritos cargados")

        self.table.setRowCount(0)

        for idx, fav in enumerate(favorites):
            fav_path = fav.get("path", fav) if isinstance(fav, dict) else fav
            recursive = fav.get("recursive", True) if isinstance(fav, dict) else True

            logger.info(
                f"_load_favorites: idx={idx}, fav_path={fav_path}, recursive={recursive}"
            )

            row = self.table.rowCount()
            self.table.insertRow(row)

            # Carpeta (columna 0)
            folder_name = os.path.basename(fav_path) or fav_path
            icon = "📂" if recursive else "📁"
            item_folder = QTableWidgetItem(f"{icon} {folder_name}")
            item_folder.setData(Qt.ItemDataRole.UserRole, fav_path)
            self.table.setItem(row, 0, item_folder)

            # Contar archivos con SQL directo
            file_count = 0
            last_scan = "-"

            try:
                conn = sqlite3.connect(db.db_path)
                cursor = conn.cursor()
                normalized_path = normalize_path(fav_path).lower()

                if recursive:
                    cursor.execute(
                        "SELECT COUNT(*), MAX(last_analyzed) FROM tracks WHERE LOWER(filepath) LIKE ?",
                        (normalized_path + "\\%",),
                    )
                else:
                    cursor.execute(
                        "SELECT COUNT(*), MAX(last_analyzed) FROM tracks WHERE LOWER(REPLACE(filepath, '\\', '/')) LIKE ?",
                        (normalized_path.replace("\\", "/") + "/%",),
                    )

                result = cursor.fetchone()
                if result:
                    file_count = result[0]
                    if result[1]:
                        last_scan = str(result[1])
                conn.close()
            except Exception as e:
                logger.error(f"Error contando tracks para {fav_path}: {e}")

            logger.info(
                f"_load_favorites: favorito {idx} '{fav_path}' -> {file_count} archivos"
            )

            # Archivos (columna 1)
            item_files = QTableWidgetItem(f"{file_count:,}".replace(",", "."))
            item_files.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self.table.setItem(row, 1, item_files)

            # Última vez escaneado (columna 2)
            self.table.setItem(row, 2, QTableWidgetItem(last_scan))

            # Path completo (columna 3)
            item_path = QTableWidgetItem(fav_path)
            item_path.setForeground(Qt.GlobalColor.gray)
            self.table.setItem(row, 3, item_path)

    def _show_context_menu(self, pos):
        """Muestra el menú contextual."""
        row = self.table.currentRow()
        if row < 0:
            return

        path_item = self.table.item(row, 0)
        if not path_item:
            return

        fav_path = path_item.data(Qt.ItemDataRole.UserRole)
        if not fav_path:
            return

        menu = QMenu(self)

        # Escanear (cerrar diálogo)
        scan_action = QAction("🔍 Escanear (cerrar y escanear)", menu)
        scan_action.triggered.connect(lambda: self._scan_folder(fav_path))
        menu.addAction(scan_action)

        # Escanear sin cerrar
        scan_keep_action = QAction("🔍 Escanear (mantener abierto)", menu)
        scan_keep_action.triggered.connect(lambda: self._scan_folder_no_close(fav_path))
        menu.addAction(scan_keep_action)

        menu.addSeparator()

        # Información (Propiedades de Windows)
        info_action = QAction("ℹ️ Propiedades (Información)", menu)
        info_action.triggered.connect(lambda: self._show_folder_info(fav_path))
        menu.addAction(info_action)

        # Abrir en Explorador
        open_action = QAction("📂 Abrir en Explorador", menu)
        open_action.triggered.connect(lambda: self._open_in_explorer(fav_path))
        menu.addAction(open_action)

        menu.addSeparator()

        # Duplicados en este favorito
        dup_action = QAction("🔍 Duplicados en este favorito", menu)
        dup_action.triggered.connect(lambda: self._show_dupes_in_favorite(fav_path))
        menu.addAction(dup_action)

        menu.addSeparator()

        # Renombrar referencia
        rename_action = QAction("✏️ Cambiar ruta (referencia)", menu)
        rename_action.triggered.connect(lambda: self._rename_favorite(fav_path))
        menu.addAction(rename_action)

        menu.addSeparator()

        # Eliminar de favoritos (solo de la lista)
        remove_action = QAction("❌ Eliminar de favoritos", menu)
        remove_action.triggered.connect(lambda: self._remove_favorite(fav_path))
        menu.addAction(remove_action)

        menu.addSeparator()

        # Eliminar archivos + favoritos (peligroso)
        delete_action = QAction("💀 Eliminar archivos + favorito (¡PELIGRO!)", menu)
        delete_action.triggered.connect(
            lambda: self._delete_files_and_favorite(fav_path)
        )
        menu.addAction(delete_action)

        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _show_folder_info(self, fav_path):
        """Muestra información de la carpeta (como Propiedades de Windows)."""
        if not os.path.exists(fav_path):
            QMessageBox.warning(self, "Error", "La carpeta no existe.")
            return

        try:
            total_files = 0
            total_size = 0
            total_folders = 0

            for root, dirs, files in os.walk(fav_path):
                total_folders += len(dirs)
                for f in files:
                    total_files += 1
                    try:
                        fp = os.path.join(root, f)
                        total_size += os.path.getsize(fp)
                    except Exception:
                        pass

            # Obtener fechas
            import datetime

            created = datetime.datetime.fromtimestamp(os.path.getctime(fav_path))
            modified = datetime.datetime.fromtimestamp(os.path.getmtime(fav_path))

            # Tamaño formateado
            def format_size(size):
                for unit in ["B", "KB", "MB", "GB", "TB"]:
                    if size < 1024:
                        return f"{size:.2f} {unit}"
                    size /= 1024
                return f"{size:.2f} PB"

            info_text = f"""📁 <b>{os.path.basename(fav_path)}</b>

📍 <b>Ruta:</b> {fav_path}

📊 <b>Estadísticas:</b>
   • Archivos: {total_files:,}
   • Subcarpetas: {total_folders}
   • Tamaño total: {format_size(total_size)}

📅 <b>Fechas:</b>
   • Creación: {created.strftime("%d/%m/%Y %H:%M:%S")}
   • Modificación: {modified.strftime("%d/%m/%Y %H:%M:%S")}

💾 <b>Atributos:</b>
   • {"📂" if total_folders > 0 else "📄"} Carpeta {"(con subcarpetas)" if total_folders > 0 else "(vacía)"}"""

            QMessageBox.information(self, "ℹ️ Propiedades", info_text)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al obtener información: {e}")

    def _open_in_explorer(self, fav_path):
        """Abre la carpeta en el Explorador de Windows."""
        import logging

        logger = logging.getLogger(__name__)
        import subprocess

        try:
            # Verificar que el path no esté vacío
            if not fav_path or fav_path.strip() == "":
                logger.error(f"_open_in_explorer: path vacío: '{fav_path}'")
                QMessageBox.warning(self, "Error", "La ruta de la carpeta está vacía.")
                return

            # Convertir a path nativo (backslashes en Windows)
            norm_path = os.path.normpath(fav_path)
            logger.info(
                f"_open_in_explorer: original='{fav_path}', normalized='{norm_path}'"
            )

            # Asegurarse de que el path esté entre comillas para manejar espacios
            quoted_path = f'"{norm_path}"'
            logger.info(f"_open_in_explorer: abriendo {quoted_path}")

            if os.name == "nt":
                # Usar explorer con el path específico
                command = f"explorer {quoted_path}"
                logger.info(f"_open_in_explorer: ejecutando '{command}'")
                result = subprocess.Popen(command, shell=True)
                logger.info(f"_open_in_explorer: resultado PID={result.pid}")
            else:
                subprocess.Popen(["xdg-open", fav_path])

        except Exception as e:
            logger.error(
                f"_open_in_explorer: error al abrir '{fav_path}': {e}", exc_info=True
            )
            QMessageBox.warning(
                self,
                "Error",
                f"No se pudo abrir la carpeta:\n{e!s}\n\nPath: {fav_path}",
            )

    def _scan_folder(self, fav_path):
        """Escanea una carpeta de favorito."""
        # Verificar que la carpeta existe
        if not os.path.exists(fav_path):
            QMessageBox.warning(self, "Error", f"La carpeta no existe:\n{fav_path}")
            return

        # Mostrar mensaje de inicio
        recursive_txt = "con subcarpetas" if self.scan_subfolders else "sin subcarpetas"
        self.lbl_info.setText(
            f"🔍 Escaneando: {os.path.basename(fav_path)} ({recursive_txt})..."
        )
        self.lbl_info.repaint()

        # Buscar la ventana principal
        main_window = self.parent()
        while main_window and not hasattr(main_window, "start_batch_analysis"):
            main_window = main_window.parent()

        if main_window and hasattr(main_window, "start_batch_analysis"):
            # Cerrar el diálogo y empezar escaneo
            self.close()
            recursive = self.scan_subfolders
            main_window.start_batch_analysis([fav_path], recursive=recursive)
        else:
            # Fallback: intentar encontrar via QApplication
            from PySide6.QtWidgets import QApplication

            for widget in QApplication.topLevelWidgets():
                if hasattr(widget, "start_batch_analysis"):
                    self.close()
                    widget.start_batch_analysis(
                        [fav_path], recursive=self.scan_subfolders
                    )
                    return

            QMessageBox.warning(
                self,
                "Error",
                "No se pudo encontrar la ventana principal para iniciar el escaneo.",
            )

    def _scan_folder_no_close(self, fav_path):
        """Escanea sin cerrar el diálogo y actualiza después."""
        if not os.path.exists(fav_path):
            QMessageBox.warning(self, "Error", f"La carpeta no existe:\n{fav_path}")
            return

        recursive_txt = "con subcarpetas" if self.scan_subfolders else "sin subcarpetas"
        self.lbl_info.setText(
            f"🔍 Iniciando escaneo: {os.path.basename(fav_path)} ({recursive_txt})..."
        )
        self.lbl_info.repaint()

        # Iniciar timer de refresco
        self.refresh_timer.start()

        main_window = self.parent()
        while main_window and not hasattr(main_window, "start_batch_analysis"):
            main_window = main_window.parent()

        # Guardar referencias para seguimiento del escaneo
        self._scanning_fav_path = fav_path
        self._scanning_main_window = main_window

        if main_window and hasattr(main_window, "start_batch_analysis"):
            recursive = self.scan_subfolders
            main_window.start_batch_analysis([fav_path], recursive=recursive)
            self.lbl_info.setText(
                f"✅ Escaneo iniciado: {os.path.basename(fav_path)}\n🔄 Actualizando automáticamente..."
            )
        else:
            from PySide6.QtWidgets import QApplication

            for widget in QApplication.topLevelWidgets():
                if hasattr(widget, "start_batch_analysis"):
                    widget.start_batch_analysis(
                        [fav_path], recursive=self.scan_subfolders
                    )
                    self.lbl_info.setText(
                        f"✅ Escaneo iniciado: {os.path.basename(fav_path)}\n🔄 Actualizando automáticamente..."
                    )
                    return

            QMessageBox.warning(
                self, "Error", "No se pudo encontrar la ventana principal."
            )

    def _on_item_double_clicked(self, item):
        """Maneja el doble clic en una fila."""
        row = item.row()
        if row >= 0:
            path_item = self.table.item(row, 0)
            if path_item:
                fav_path = path_item.data(Qt.ItemDataRole.UserRole)
                self._scan_folder(fav_path)

    def _scan_selected(self):
        """Escanea el favorito seleccionado o el primero si no hay selección."""
        row = self.table.currentRow()

        # Si no hay selección, tomar el primero
        row = max(row, 0)

        if self.table.rowCount() == 0:
            QMessageBox.information(self, "Info", "No hay favoritos para escanear.")
            return

        path_item = self.table.item(row, 0)
        if path_item:
            fav_path = path_item.data(Qt.ItemDataRole.UserRole)
            self._scan_folder(fav_path)

    def _on_info_clicked(self):
        """Muestra información de la carpeta seleccionada."""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Info", "Selecciona una carpeta primero.")
            return

        path_item = self.table.item(row, 0)
        if path_item:
            fav_path = path_item.data(Qt.ItemDataRole.UserRole)
            if fav_path:
                self._show_folder_info(fav_path)

    def _on_open_clicked(self):
        """Abre la carpeta seleccionada en el Explorador."""
        import logging

        logger = logging.getLogger(__name__)

        row = self.table.currentRow()
        logger.info(f"_on_open_clicked: row={row}, rowCount={self.table.rowCount()}")

        if row < 0:
            # Si no hay selección, intentar usar la primera fila
            if self.table.rowCount() > 0:
                row = 0
                logger.info(f"_on_open_clicked: usando row={row} (primera fila)")
            else:
                QMessageBox.information(
                    self,
                    "Info",
                    "No hay carpetas en la lista. Añade carpetas favoritas primero.",
                )
                return

        path_item = self.table.item(row, 0)
        if not path_item:
            logger.warning(f"_on_open_clicked: path_item es None para row={row}")
            QMessageBox.warning(
                self,
                "Error",
                f"No se pudo obtener la información de la carpeta (fila {row}).",
            )
            return

        fav_path = path_item.data(Qt.ItemDataRole.UserRole)
        logger.info(f"_on_open_clicked: fav_path='{fav_path}', type={type(fav_path)}")

        if not fav_path:
            logger.warning(f"_on_open_clicked: fav_path está vacío para row={row}")
            QMessageBox.warning(self, "Error", "La ruta de la carpeta está vacía.")
            return

        # Verificar que el path existe
        if not os.path.exists(fav_path):
            logger.warning(f"_on_open_clicked: fav_path no existe: '{fav_path}'")
            reply = QMessageBox.question(
                self,
                "Carpeta no encontrada",
                f"La carpeta no existe:\n{fav_path}\n\n¿Quieres eliminarla de favoritos?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._remove_favorite(fav_path)
            return

        logger.info(f"_on_open_clicked: abriendo '{fav_path}'")
        self._open_in_explorer(fav_path)

    def _on_delete_clicked(self):
        """Elimina la carpeta seleccionada de favoritos."""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Info", "Selecciona una carpeta primero.")
            return

        path_item = self.table.item(row, 0)
        if path_item:
            fav_path = path_item.data(Qt.ItemDataRole.UserRole)
            if fav_path:
                self._remove_favorite(fav_path)

    def _on_subfolders_changed(self, state):
        """Maneja el cambio del checkbox de subcarpetas."""
        self.scan_subfolders = state == Qt.CheckState.Checked

    def _show_dupes_in_favorite(self, fav_path):
        """Busca duplicados solo en este favorito."""
        from services.db import get_db

        db = get_db()
        all_rows = db.get_all_tracks()

        # Filtrar solo archivos de favoritos
        # Normalizar paths para evitar problemas con separadores (\ vs /)
        fav_path_normalized = self._normalize_path(fav_path)
        fav_path_with_slash = (
            fav_path_normalized + "\\"
            if not fav_path_normalized.endswith("\\")
            else fav_path_normalized
        )

        favorite_files = {}
        for row in all_rows:
            filepath = row.get("filepath")
            if filepath:
                filepath_normalized = self._normalize_path(filepath)
                if filepath_normalized.startswith(fav_path_with_slash):
                    favorite_files[filepath] = row

        if not favorite_files:
            QMessageBox.information(
                self, "Duplicados", "No hay archivos en la BD para esta carpeta."
            )
            return

        # Crear objetos MusicFile
        from core.reader.mp3_reader import MP3Reader

        analyzed = {}
        for fp, row in favorite_files.items():
            try:
                mf = MP3Reader._from_db_row(row)
                analyzed[fp] = mf
            except Exception:
                pass

        if self.parent():
            from ui.dialogs.duplicate_dialog import DuplicateDialog

            dlg = DuplicateDialog(analyzed, self.parent())
            dlg.setWindowTitle(f"Duplicados en favorito: {os.path.basename(fav_path)}")
            dlg.exec()

    def _rename_favorite(self, fav_path):
        """Permite cambiar la ruta del favorito."""
        from PySide6.QtWidgets import QFileDialog

        new_path = QFileDialog.getExistingDirectory(
            self, "Seleccionar nueva ubicación", fav_path
        )

        if new_path and new_path != fav_path:
            # Verificar que existe
            if not os.path.isdir(new_path):
                QMessageBox.warning(self, "Error", "La carpeta no existe.")
                return

            # Actualizar
            self.bookmarks_manager.remove_bookmark(fav_path)
            self.bookmarks_manager.add_bookmark(new_path)
            self._load_favorites()
            QMessageBox.information(self, "Éxito", "Referencia actualizada.")

    def _remove_favorite(self, fav_path):
        """Elimina el favorito de la lista (no borra archivos)."""
        reply = QMessageBox.question(
            self,
            "Confirmar",
            f"¿Eliminar '{os.path.basename(fav_path)}' de favoritos?\n\nLos archivos NO serán borrados.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.bookmarks_manager.remove_bookmark(fav_path)
            self._load_favorites()

    def _delete_files_and_favorite(self, fav_path):
        """¡PELIGRO! Borra los archivos y el favorito."""
        reply = QMessageBox.critical(
            self,
            "⚠️ ¡PELIGRO!",
            f"¿SEGURO QUE QUIERES BORRAR TODO?\n\n"
            f"Carpeta: {fav_path}\n\n"
            f"Esto borrará TODOS los archivos MP3 de esta carpeta Y la eliminará de favoritos.\n"
            f"¡ESTA ACCIÓN NO SE PUEDE DESHACER!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Segunda confirmación con input
        from PySide6.QtWidgets import QInputDialog, QLineEdit

        text, ok = QInputDialog.getText(
            self,
            "Última confirmación",
            "Escribe 'SI' en mayúsculas para confirmar:",
            QLineEdit.EchoMode.Normal,
            "",
        )

        if not ok or text.strip() != "SI":
            QMessageBox.information(
                self, "Cancelado", "Operación cancelada. No se escribió 'SI'."
            )
            return

        # Por ahora, simplificado: solo preguntar una vez
        try:
            deleted = 0
            errors = 0

            for root, dirs, files in os.walk(fav_path):
                for f in files:
                    if f.lower().endswith(".mp3"):
                        fp = os.path.join(root, f)
                        try:
                            os.remove(fp)
                            deleted += 1
                        except Exception:
                            errors += 1

            # Eliminar carpeta si está vacía
            try:
                os.rmdir(fav_path)
            except Exception:
                pass  # Puede que no esté vacía

            # Eliminar de favoritos
            self.bookmarks_manager.remove_bookmark(fav_path)

            # Eliminar de la base de datos
            from services.db import get_db

            db = get_db()
            # Esto eliminaría los tracks... we'd need to add a method

            self._load_favorites()

            QMessageBox.information(
                self, "Resultado", f"Archivos borrados: {deleted}\nErrores: {errors}"
            )

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al borrar: {e}")
