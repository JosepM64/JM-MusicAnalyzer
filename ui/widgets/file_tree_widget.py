import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QTreeWidget, QTreeWidgetItem


class FileTreeWidget(QTreeWidget):
    """
    Widget de árbol de archivos para navegación y gestión de carpetas.
    """

    folderSelected = Signal(str)
    folderClicked = Signal(str)
    fileDropped = Signal(str)
    addToFavorites = Signal(str, bool)
    rescanFolder = Signal(str, bool)

    def __init__(self):
        super().__init__()
        self.setHeaderHidden(False)
        self.setHeaderLabels(["Carpetas"])
        self.setAlternatingRowColors(True)
        self.setAnimated(True)
        self.setIndentation(20)

        self._clipboard = []
        self._clipboard_cut = False

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)

        self.itemClicked.connect(self._on_item_clicked)
        self.itemExpanded.connect(self._on_item_expanded)

    def _on_item_expanded(self, item):
        """Carga los hijos cuando se expande un elemento."""
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if not path or not os.path.isdir(path):
            return

        if item.childCount() == 1 and item.child(0).text(0) == "Cargando...":
            item.takeChildren()
            self._add_child_items(item, path)

    def load_folder_tree(self, root_path: str):
        """Carga el árbol de carpetas desde una ruta raíz."""
        self.clear()
        if not root_path or not os.path.isdir(root_path):
            return

        root_name = os.path.basename(root_path)
        if not root_name:
            root_name = root_path

        root_item = QTreeWidgetItem(self, [root_name])
        root_item.setData(0, Qt.ItemDataRole.UserRole, root_path)
        root_item.setIcon(0, self._folder_icon())
        root_item.setExpanded(True)

        self._add_child_items(root_item, root_path)

        self.addTopLevelItem(root_item)

    def load_favorites_tree(self, bookmarks: list):
        """Carga el árbol mostrando cada favorito como raíz."""
        self.clear()
        if not bookmarks:
            return

        for bookmark in bookmarks:
            path = (
                bookmark.get("path", bookmark)
                if isinstance(bookmark, dict)
                else bookmark
            )
            recursive = (
                bookmark.get("recursive", True) if isinstance(bookmark, dict) else True
            )

            if not os.path.isdir(path):
                continue

            root_name = os.path.basename(path)
            if not root_name:
                root_name = path
            icon = "📂" if recursive else "📁"

            root_item = QTreeWidgetItem(self, [f"{icon} {root_name}"])
            root_item.setData(0, Qt.ItemDataRole.UserRole, path)
            root_item.setIcon(0, self._folder_icon())
            root_item.setExpanded(False)

            placeholder = QTreeWidgetItem(root_item, ["Cargando..."])
            placeholder.setData(0, Qt.ItemDataRole.UserRole, None)

            self.addTopLevelItem(root_item)

    def _add_child_items(self, parent_item, parent_path):
        """Añade elementos hijos recursivamente."""
        try:
            items = sorted(os.listdir(parent_path))
        except Exception as e:
            print(f"Error listing: {e}")
            return

        for item_name in items:
            item_path = os.path.join(parent_path, item_name)
            if os.path.isdir(item_path):
                child_item = QTreeWidgetItem(parent_item, [item_name])
                child_item.setData(0, Qt.ItemDataRole.UserRole, item_path)
                child_item.setIcon(0, self._folder_icon())

                try:
                    subitems = os.listdir(item_path)
                    has_subdirs = any(
                        os.path.isdir(os.path.join(item_path, s)) for s in subitems
                    )
                    if has_subdirs:
                        placeholder = QTreeWidgetItem(child_item, ["Cargando..."])
                        placeholder.setData(0, Qt.ItemDataRole.UserRole, None)
                except Exception:
                    pass

                parent_item.addChild(child_item)

    def _on_item_clicked(self, item, column):
        """Maneja el clic en un elemento para filtrar."""
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if path and os.path.isdir(path):
            self.folderClicked.emit(path)

    def _folder_icon(self):
        from PySide6.QtGui import QIcon

        return QIcon.fromTheme("folder", QIcon(":/qticons/"))

    def _show_context_menu(self, pos):
        item = self.itemAt(pos)
        if not item:
            return

        path = item.data(0, Qt.ItemDataRole.UserRole)
        if not path or not os.path.isdir(path):
            return

        menu = QMenu(self)

        fav_menu = QMenu("⭐ Añadir a Favoritos", menu)

        fav_no_sub = QAction("📁 Solo esta carpeta", fav_menu)
        fav_no_sub.triggered.connect(lambda: self.addToFavorites.emit(path, False))
        fav_menu.addAction(fav_no_sub)

        fav_with_sub = QAction("📂 Con subcarpetas", fav_menu)
        fav_with_sub.triggered.connect(lambda: self.addToFavorites.emit(path, True))
        fav_menu.addAction(fav_with_sub)

        menu.addMenu(fav_menu)

        menu.addSeparator()

        rescan_menu = QMenu("🔄 Reescanear", menu)

        rescan_no_sub = QAction("📁 Solo esta carpeta", rescan_menu)
        rescan_no_sub.triggered.connect(lambda: self.rescanFolder.emit(path, False))
        rescan_menu.addAction(rescan_no_sub)

        rescan_with_sub = QAction("📂 Con subcarpetas", rescan_menu)
        rescan_with_sub.triggered.connect(lambda: self.rescanFolder.emit(path, True))
        rescan_menu.addAction(rescan_with_sub)

        menu.addMenu(rescan_menu)

        menu.addSeparator()

        copy_action = QAction("📋 Copiar", menu)
        copy_action.triggered.connect(lambda: self._copy_to_clipboard(path))
        menu.addAction(copy_action)

        cut_action = QAction("✂️ Cortar", menu)
        cut_action.triggered.connect(lambda: self._cut_to_clipboard(path))
        menu.addAction(cut_action)

        if self._clipboard:
            paste_action = QAction("📥 Pegar aquí", menu)
            paste_action.triggered.connect(lambda: self._paste_to_folder(path))
            menu.addAction(paste_action)

        menu.addSeparator()

        open_action = QAction("📂 Abrir en Explorador", menu)
        open_action.triggered.connect(lambda: self._open_in_explorer(path))
        menu.addAction(open_action)

        menu.exec(self.mapToGlobal(pos))

    def _copy_to_clipboard(self, path):
        self._clipboard = [path]
        self._clipboard_cut = False

    def _cut_to_clipboard(self, path):
        self._clipboard = [path]
        self._clipboard_cut = True

    def _paste_to_folder(self, dest_folder):
        if not self._clipboard:
            return
        import shutil

        for src in self._clipboard:
            try:
                if os.path.isdir(src):
                    dest = os.path.join(dest_folder, os.path.basename(src))
                    if self._clipboard_cut:
                        shutil.move(src, dest)
                    else:
                        shutil.copytree(src, dest, dirs_exist_ok=True)
                else:
                    dest = os.path.join(dest_folder, os.path.basename(src))
                    if self._clipboard_cut:
                        shutil.move(src, dest)
                    else:
                        shutil.copy2(src, dest)
            except Exception as e:
                print(f"Error pegando {src}: {e}")
        self._clipboard = []

    def _open_in_explorer(self, path):
        import subprocess

        if os.name == "nt":
            subprocess.Popen(f'explorer "{path}"')
        elif os.name == "posix":
            subprocess.Popen(["xdg-open", path])

    def expandItem(self, item):
        """Override to load children when expanded."""
        super().expandItem(item)
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if path and os.path.isdir(path):
            if item.childCount() == 1 and item.child(0).text(0) == "...":
                item.takeChildren()
                self._add_child_items(item, path)
