import os

from PySide6.QtCore import QStringListModel, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.models import MetadataInfo
from services.bookmarks_manager import BookmarksManager
from ui.styles import INPUT_FIELD_STYLE
from ui.widgets.rating_widget import RatingWidget

_ACTION_BTN = """
QPushButton {{
    background-color: {bg};
    color: {fg};
    font-size: 10px;
    font-weight: {fw};
    padding: 3px 8px;
    border-radius: 3px;
    border: none;
}}
QPushButton:hover {{ background-color: {hover}; }}
QPushButton:disabled {{ background-color: #555; color: #777; }}
"""


class MetadataPanel(QGroupBox):
    saveRequested = Signal(dict)
    identifyRequested = Signal()
    fingerprintRequested = Signal(str)
    addFolderRequested = Signal(bool)
    bookmarkFolderRequested = Signal(str)
    bookmarkSelected = Signal(str)

    def __init__(self):
        super().__init__("Metadatos")
        self.fields = {}
        self._existing_genres = set()
        self._existing_artists = set()
        self._existing_titles = set()
        self._current_favorite_path = None
        self._current_filepath = None
        self._batch_count = 0
        self._original_data = {}
        self._modified_fields = set()
        self.bookmarks_manager = BookmarksManager()
        self.rating_edit = RatingWidget(star_size=16, editable=True)
        self._setup_ui()
        self._connect_field_signals()
        self.refresh_bookmarks()
        self._load_suggestions_from_db()

    def _connect_field_signals(self):
        for key, widget in self.fields.items():
            widget.textChanged.connect(lambda text, k=key: self._mark_field_modified(k))

    def _mark_field_modified(self, field):
        self._modified_fields.add(field)

    def _load_suggestions_from_db(self):
        try:
            from services.db import get_db

            db = get_db()
            genres = db.get_unique_genres()
            artists = db.get_unique_artists()
            self._existing_genres.update(genres)
            self._existing_artists.update(artists)
            self.genre_completer.setModel(
                QStringListModel(sorted(self._existing_genres))
            )
            self.artist_completer.setModel(
                QStringListModel(sorted(self._existing_artists))
            )
        except Exception as e:
            import logging

            logging.getLogger(__name__).error(f"Error cargando sugerencias de DB: {e}")

    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(6, 8, 6, 6)
        self.main_layout.setSpacing(4)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(3)

        lbl_style = "font-size: 9px; color: #888; font-weight: bold;"

        row = 0
        grid.addWidget(QLabel("Título"), row, 0)
        self.fields["title"] = QLineEdit()
        self.fields["title"].setMaximumHeight(20)
        self.fields["title"].setStyleSheet(INPUT_FIELD_STYLE)
        grid.addWidget(self.fields["title"], row, 1, 1, 5)

        row = 1
        grid.addWidget(QLabel("Artista"), row, 0)
        self.fields["artist"] = QLineEdit()
        self.fields["artist"].setMaximumHeight(20)
        self.fields["artist"].setStyleSheet(INPUT_FIELD_STYLE)
        grid.addWidget(self.fields["artist"], row, 1, 1, 3)

        grid.addWidget(QLabel("Álbum"), row, 4)
        self.fields["album"] = QLineEdit()
        self.fields["album"].setMaximumHeight(20)
        self.fields["album"].setStyleSheet(INPUT_FIELD_STYLE)
        grid.addWidget(self.fields["album"], row, 5, 1, 3)

        row = 2
        grid.addWidget(QLabel("Género"), row, 0)
        self.fields["genre"] = QLineEdit()
        self.fields["genre"].setMaximumHeight(20)
        self.fields["genre"].setStyleSheet(INPUT_FIELD_STYLE)
        grid.addWidget(self.fields["genre"], row, 1, 1, 2)

        grid.addWidget(QLabel("BPM"), row, 3)
        self.fields["bpm"] = QLineEdit()
        self.fields["bpm"].setMaximumHeight(20)
        self.fields["bpm"].setMaximumWidth(45)
        self.fields["bpm"].setStyleSheet(INPUT_FIELD_STYLE)
        grid.addWidget(self.fields["bpm"], row, 4)

        grid.addWidget(QLabel("Año"), row, 5)
        self.fields["year"] = QLineEdit()
        self.fields["year"].setMaximumHeight(20)
        self.fields["year"].setMaximumWidth(45)
        self.fields["year"].setStyleSheet(INPUT_FIELD_STYLE)
        grid.addWidget(self.fields["year"], row, 6)

        grid.addWidget(QLabel("Trk"), row, 7)
        self.fields["track_number"] = QLineEdit()
        self.fields["track_number"].setMaximumHeight(20)
        self.fields["track_number"].setMaximumWidth(30)
        self.fields["track_number"].setStyleSheet(INPUT_FIELD_STYLE)
        grid.addWidget(self.fields["track_number"], row, 8)

        row = 3
        rating_box = QWidget()
        rl = QHBoxLayout(rating_box)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(2)
        lbl_r = QLabel("★")
        lbl_r.setStyleSheet("font-size: 13px; color: #FFD700;")
        rl.addWidget(lbl_r)
        rl.addWidget(self.rating_edit)
        rl.addStretch()
        grid.addWidget(rating_box, row, 0, 1, 2)

        grid.addWidget(QLabel("Comentario"), row, 2)
        self.fields["comment"] = QLineEdit()
        self.fields["comment"].setMaximumHeight(20)
        self.fields["comment"].setStyleSheet(INPUT_FIELD_STYLE)
        grid.addWidget(self.fields["comment"], row, 3, 1, 6)

        for r in range(4):
            lbl_item = grid.itemAtPosition(r, 0)
            if lbl_item and lbl_item.widget():
                lbl_item.widget().setStyleSheet(lbl_style)
        for c in [2, 3, 4, 5, 7]:
            lbl_item = grid.itemAtPosition(1, c)
            if lbl_item and lbl_item.widget():
                lbl_item.widget().setStyleSheet(lbl_style)
        for c in [2, 3, 5, 7]:
            lbl_item = grid.itemAtPosition(2, c)
            if lbl_item and lbl_item.widget():
                lbl_item.widget().setStyleSheet(lbl_style)
        lbl_item = grid.itemAtPosition(3, 2)
        if lbl_item and lbl_item.widget():
            lbl_item.widget().setStyleSheet(lbl_style)

        self.main_layout.addLayout(grid)

        # --- Action bar: Buscar + Fingerprint + Guardar ---
        action_row = QHBoxLayout()
        action_row.setSpacing(4)

        self.btn_identify = QPushButton("\U0001f50d Buscar")
        self.btn_identify.setToolTip("Buscar por texto en MusicBrainz/iTunes")
        self.btn_identify.setFixedHeight(22)
        self.btn_identify.setStyleSheet(
            _ACTION_BTN.format(bg="#6a1b9a", fg="white", fw="bold", hover="#8e24aa")
        )
        self.btn_identify.setEnabled(False)
        self.btn_identify.clicked.connect(lambda: self.identifyRequested.emit())
        action_row.addWidget(self.btn_identify)

        self.btn_fingerprint = QPushButton("\U0001f3b5 Fingerprint")
        self.btn_fingerprint.setToolTip("Identificar por huella acústica (AcoustID)")
        self.btn_fingerprint.setFixedHeight(22)
        self.btn_fingerprint.setStyleSheet(
            _ACTION_BTN.format(bg="#00796b", fg="white", fw="bold", hover="#00897b")
        )
        self.btn_fingerprint.setEnabled(False)
        self.btn_fingerprint.clicked.connect(self._on_fingerprint_clicked)
        action_row.addWidget(self.btn_fingerprint)

        action_row.addStretch()

        self.lbl_batch_count = QLabel("")
        self.lbl_batch_count.setStyleSheet(
            "color: #ffcc00; font-size: 10px; font-weight: bold; padding: 0 4px;"
        )
        action_row.addWidget(self.lbl_batch_count)

        self.btn_save = QPushButton("\U0001f4be GUARDAR")
        self.btn_save.setFixedHeight(22)
        self.btn_save.setEnabled(False)
        self.btn_save.setStyleSheet(
            _ACTION_BTN.format(bg="#0078d4", fg="white", fw="bold", hover="#1e88e5")
        )
        self.btn_save.clicked.connect(self._on_save_clicked)
        action_row.addWidget(self.btn_save)

        self.main_layout.addLayout(action_row)

        # --- Separator ---
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #444;")
        self.main_layout.addWidget(sep)

        # --- Imports row: Favoritos + Carpetas ---
        import_row = QHBoxLayout()
        import_row.setSpacing(3)

        self.combo_bookmarks = QComboBox()
        self.combo_bookmarks.setPlaceholderText("\u2b50 Favoritos...")
        self.combo_bookmarks.setMinimumWidth(100)
        self.combo_bookmarks.setMaximumWidth(140)
        self.combo_bookmarks.setStyleSheet(
            "QComboBox { font-size: 9px; padding: 2px; }"
        )
        self.combo_bookmarks.currentIndexChanged.connect(self._on_bookmark_selected)
        import_row.addWidget(self.combo_bookmarks)

        self.btn_add_bookmark = QPushButton("+\u2b50")
        self.btn_add_bookmark.setToolTip("Añadir carpeta a favoritos")
        self.btn_add_bookmark.setFixedSize(26, 22)
        self.btn_add_bookmark.setStyleSheet(
            _ACTION_BTN.format(bg="#555", fg="white", fw="normal", hover="#777")
        )
        self.btn_add_bookmark.clicked.connect(self._on_add_bookmark_clicked)
        import_row.addWidget(self.btn_add_bookmark)

        self.btn_manage_favorites = QPushButton("\u2699")
        self.btn_manage_favorites.setToolTip("Gestionar favoritos")
        self.btn_manage_favorites.setFixedSize(26, 22)
        self.btn_manage_favorites.setStyleSheet(
            _ACTION_BTN.format(bg="#555", fg="white", fw="normal", hover="#777")
        )
        self.btn_manage_favorites.clicked.connect(self._on_manage_favorites_clicked)
        import_row.addWidget(self.btn_manage_favorites)

        import_row.addSpacing(6)

        self.btn_add_dir = QPushButton("\U0001f4c1 +Carp")
        self.btn_add_dir.setToolTip("Añadir carpeta (sin subcarpetas)")
        self.btn_add_dir.setFixedHeight(22)
        self.btn_add_dir.setStyleSheet(
            _ACTION_BTN.format(bg="#444", fg="#ccc", fw="normal", hover="#666")
        )
        self.btn_add_dir.clicked.connect(lambda: self.addFolderRequested.emit(False))
        import_row.addWidget(self.btn_add_dir)

        self.btn_add_tree = QPushButton("\U0001f4c2 +Sub")
        self.btn_add_tree.setToolTip("Añadir con subcarpetas")
        self.btn_add_tree.setFixedHeight(22)
        self.btn_add_tree.setStyleSheet(
            _ACTION_BTN.format(bg="#444", fg="#ccc", fw="normal", hover="#666")
        )
        self.btn_add_tree.clicked.connect(lambda: self.addFolderRequested.emit(True))
        import_row.addWidget(self.btn_add_tree)

        import_row.addStretch()

        self.lbl_current_folder = QLabel("")
        self.lbl_current_folder.setStyleSheet("color: #666; font-size: 9px;")
        self.lbl_current_folder.setMaximumWidth(120)
        import_row.addWidget(self.lbl_current_folder)

        self.main_layout.addLayout(import_row)

        # Autocompletado
        self.genre_completer = QCompleter([])
        self.genre_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.genre_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.fields["genre"].setCompleter(self.genre_completer)

        self.artist_completer = QCompleter([])
        self.artist_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.artist_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.fields["artist"].setCompleter(self.artist_completer)

        self.title_completer = QCompleter([])
        self.title_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.title_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.fields["title"].setCompleter(self.title_completer)

        self.setMaximumHeight(280)

    def refresh_bookmarks(self):
        self.combo_bookmarks.blockSignals(True)
        self.combo_bookmarks.clear()
        self.combo_bookmarks.addItem("\u2b50 Favoritos...")
        for bookmark in self.bookmarks_manager.load_bookmarks():
            path = (
                bookmark.get("path", bookmark)
                if isinstance(bookmark, dict)
                else bookmark
            )
            recursive = (
                bookmark.get("recursive", True) if isinstance(bookmark, dict) else True
            )
            icon = "\U0001f4c2" if recursive else "\U0001f4c1"
            self.combo_bookmarks.addItem(f"{icon} {os.path.basename(path)}", path)
        self.combo_bookmarks.blockSignals(False)

    def _on_bookmark_selected(self, index):
        if index <= 0:
            return
        path = self.combo_bookmarks.itemData(index)
        if path:
            self.bookmarkFolderRequested.emit(path)
            self.bookmarkSelected.emit(path)
            self.set_current_folder_label(path)
            self.combo_bookmarks.setCurrentIndex(0)

    def set_current_folder_label(self, path):
        if path:
            folder_name = os.path.basename(path)
            if not folder_name:
                folder_name = path
            self.lbl_current_folder.setText(f"\U0001f4c1 {folder_name}")
            self._current_favorite_path = path
        else:
            self.lbl_current_folder.setText("")
            self._current_favorite_path = None

    def _load_suggestions_from_folder(self, folder_path):
        try:
            from services.db import get_db

            db = get_db()
            unique_values = db.get_unique_values_by_folder(folder_path)
            genres = set(unique_values.get("genre", []))
            artists = set(unique_values.get("artist", []))
            titles = set(unique_values.get("title", []))
            genres = {g for g in genres if g and g != "-"}
            self._existing_genres = genres
            self._existing_artists = artists
            self._existing_titles = titles
            self.genre_completer.setModel(QStringListModel(sorted(genres)))
            self.artist_completer.setModel(QStringListModel(sorted(artists)))
            self.title_completer.setModel(QStringListModel(sorted(titles)))
        except Exception as e:
            import logging

            logging.getLogger(__name__).error(f"Error cargando sugerencias: {e}")

    def _on_add_bookmark_clicked(self):
        from PySide6.QtWidgets import QFileDialog

        path = QFileDialog.getExistingDirectory(
            self, "Seleccionar carpeta para favoritos"
        )
        if path:
            if self.bookmarks_manager.add_bookmark(path):
                self.refresh_bookmarks()

    def _on_manage_favorites_clicked(self):
        from ui.dialogs.favorites_manager_dialog import FavoritesManagerDialog

        dlg = FavoritesManagerDialog(self)
        dlg.exec()
        self.refresh_bookmarks()

    def update_suggestions(self, genres: list):
        if genres:
            self._existing_genres.update([g for g in genres if g and g != "-"])
            self.genre_completer.setModel(
                QStringListModel(sorted(self._existing_genres))
            )

    def _on_save_clicked(self):
        if self._batch_count > 1 and self._modified_fields:
            data = {
                key: field.text()
                for key, field in self.fields.items()
                if key in self._modified_fields
            }
            data["rating"] = self.rating_edit.rating
        else:
            data = {key: field.text() for key, field in self.fields.items()}
            data["rating"] = self.rating_edit.rating
        self.saveRequested.emit(data)
        self._modified_fields.clear()

    def _on_fingerprint_clicked(self):
        import logging

        logger = logging.getLogger(__name__)
        logger.info(f"_on_fingerprint_clicked: filepath={self._current_filepath}")
        if self._current_filepath:
            self.fingerprintRequested.emit(self._current_filepath)
        else:
            logger.warning("_on_fingerprint_clicked: _current_filepath es None!")

    def update_data(self, metadata: MetadataInfo, filepath: str = None):
        import logging

        logger = logging.getLogger(__name__)
        title = metadata.title
        if not title and filepath:
            title = os.path.splitext(os.path.basename(filepath))[0]
        logger.info(f"update_data: title='{title}', filepath={filepath}")
        self.fields["title"].setText(title or "")
        self.fields["artist"].setText(metadata.artist or "")
        self.fields["album"].setText(metadata.album or "")
        self.fields["genre"].setText(metadata.genre or "")
        self.fields["year"].setText(metadata.year or "")
        self.fields["track_number"].setText(metadata.track_number or "")
        self.fields["bpm"].setText(str(metadata.bpm) if metadata.bpm else "")
        self.fields["comment"].setText(metadata.comment or "")
        self.rating_edit.set_rating(metadata.rating)
        self.btn_save.setEnabled(True)
        self.btn_identify.setEnabled(True)
        self.btn_fingerprint.setEnabled(True)
        self._original_data = {
            "title": title or "",
            "artist": metadata.artist or "",
            "album": metadata.album or "",
            "genre": metadata.genre or "",
            "year": metadata.year or "",
            "track_number": metadata.track_number or "",
            "bpm": str(metadata.bpm) if metadata.bpm else "",
            "comment": metadata.comment or "",
            "rating": metadata.rating,
        }
        self._modified_fields.clear()

    def set_filepath(self, filepath: str):
        import logging

        logging.getLogger(__name__).info(f"set_filepath: {filepath}")
        self._current_filepath = filepath

    def set_batch_count(self, count: int):
        self._batch_count = count
        if count > 1:
            self.lbl_batch_count.setText(f"({count})")
        else:
            self.lbl_batch_count.setText("")

    def clear(self):
        for widget in self.fields.values():
            widget.clear()
        self.rating_edit.set_rating(0)
        self.btn_save.setEnabled(False)
        self.btn_identify.setEnabled(False)
        self.btn_fingerprint.setEnabled(False)
        self.lbl_batch_count.setText("")
        self._current_filepath = None
