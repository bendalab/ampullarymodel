from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap


class KeepRatioPixmapLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = None
        self.setAlignment(Qt.AlignCenter)

    def setPixmap(self, pixmap: QPixmap):
        self._pixmap = pixmap
        self.updateScaledPixmap()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.updateScaledPixmap()

    def updateScaledPixmap(self):
        if self._pixmap:
            scaled_pix = self._pixmap.scaled(
                self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            super().setPixmap(scaled_pix)


