from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
)

from ui.styles import DARK_METADATA_DIALOG_STYLE


class TrackEditDialog(QDialog):
    """
    Fase E (v4.4.0) - Diàleg per editar metadados d'una pista.

    Permet editar títol, artista, gènere i rating amb autocompletat
    des de la base de dades.
    """

    def __init__(self, artist, title, genre, rating, db, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Editar metadatos")
        self.setMinimumWidth(450)
        self.setStyleSheet(DARK_METADATA_DIALOG_STYLE)
        self._rating_index = int(rating * 2)
        self._setup_ui(artist, title, genre, rating, db)

    def _setup_ui(self, artist, title, genre, rating, db):
        layout = QFormLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        from PySide6.QtWidgets import QCompleter

        unique_titles = db.get_unique_titles()
        unique_artists = db.get_unique_artists()
        unique_genres = db.get_unique_genres()

        self.edit_title = QLineEdit(title)
        if unique_titles:
            c = QCompleter(unique_titles, self)
            c.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            c.setFilterMode(Qt.MatchFlag.MatchContains)
            c.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
            self.edit_title.setCompleter(c)

        self.edit_artist = QLineEdit(artist)
        if unique_artists:
            c = QCompleter(unique_artists, self)
            c.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            c.setFilterMode(Qt.MatchFlag.MatchContains)
            c.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
            self.edit_artist.setCompleter(c)

        self.edit_genre = QLineEdit(genre)
        if unique_genres:
            c = QCompleter(unique_genres, self)
            c.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            c.setFilterMode(Qt.MatchFlag.MatchContains)
            c.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
            self.edit_genre.setCompleter(c)

        self.combo_rating = QComboBox()
        self.combo_rating.addItems(
            ["Sin", "★", "★½", "★★", "★★½", "★★★", "★★★½", "★★★★", "★★★★½", "★★★★★"]
        )
        self.combo_rating.setCurrentIndex(int(rating * 2))
        self.combo_rating.setStyleSheet("""
            QComboBox::item { color: gold; font-size: 14px; }
            QComboBox::item:selected { background-color: #6a1b9a; }
        """)

        layout.addRow("<span style='color: #ffffff;'>Título:</span>", self.edit_title)
        layout.addRow("<span style='color: #ffffff;'>Artista:</span>", self.edit_artist)
        layout.addRow("<span style='color: #ffffff;'>Género:</span>", self.edit_genre)
        layout.addRow("<span style='color: #ffffff;'>Rating:</span>", self.combo_rating)

        btn_box = QHBoxLayout()
        btn_box.setSpacing(15)
        btn_ok = QPushButton("💾 Guardar")
        btn_cancel = QPushButton("✖ Cancelar")

        btn_ok.setStyleSheet("""
            QPushButton {
                background-color: #6a1b9a; color: white; border: 1px solid #7b2cbf;
                border-radius: 4px; padding: 10px 20px; font-weight: bold; font-size: 13px;
            }
            QPushButton:hover { background-color: #7b2cbf; }
            QPushButton:pressed { background-color: #5a0d8a; }
        """)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #444; color: white; border: 1px solid #555;
                border-radius: 4px; padding: 10px 20px; font-weight: bold; font-size: 13px;
            }
            QPushButton:hover { background-color: #555; }
            QPushButton:pressed { background-color: #333; }
        """)

        btn_box.addStretch()
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_ok)
        layout.addRow("", btn_box)

        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)

    def get_data(self):
        return {
            "title": self.edit_title.text().strip(),
            "artist": self.edit_artist.text().strip(),
            "genre": self.edit_genre.text().strip(),
            "rating": self.combo_rating.currentIndex() / 2.0,
        }
