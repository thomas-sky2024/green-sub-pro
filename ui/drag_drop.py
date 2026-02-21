from PySide6.QtWidgets import QListWidget, QListWidgetItem, QAbstractItemView
from PySide6.QtCore import Qt, Signal
import os

class DragDropListWidget(QListWidget):
    """Custom QListWidget accepting dragged items."""
    
    files_dropped = Signal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setAlternatingRowColors(True)
        # Apply a simple stylesheet
        self.setStyleSheet("""
            QListWidget {
                background-color: #1a1a1f; 
                color: #ffffff;
                border: 1px solid #2a2a30;
                border-radius: 12px;
                padding: 10px;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            }
            QListWidget::item {
                padding: 12px;
                background-color: #25252d;
                border-radius: 8px;
                margin-bottom: 5px;
            }
            QListWidget::item:selected {
                background-color: #b3ff00;
                color: #000000;
                font-weight: bold;
            }
            QListWidget::item:hover {
                background-color: #32323b;
            }
        """)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()
            
            dropped_files = []
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    ext = os.path.splitext(file_path)[1].lower()
                    if ext in ['.srt', '.vtt', '.ass', '.mp3', '.wav', '.m4a', '.mp4', '.mov', '.mkv']:
                        dropped_files.append(file_path)
            
            if dropped_files:
                self.files_dropped.emit(dropped_files)
        else:
            event.ignore()

    def add_unique_items(self, file_paths):
        existing_paths = [self.item(i).data(Qt.UserRole) for i in range(self.count())]
        for path in file_paths:
            if path not in existing_paths:
                filename = os.path.basename(path)
                item = QListWidgetItem(filename)
                item.setData(Qt.UserRole, path)
                self.addItem(item)
