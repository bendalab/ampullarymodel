
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Slot, Qt, QSize

from ampullary_ui.ui import Ui_LoadingSplash

class SplashPage(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self._ui = Ui_LoadingSplash()
        self._ui.setupUi(self)

        self._icon_width = 0.25
        self._max_icon_height = 0.85
        self._pixmap = QPixmap(":/icons/icon")
        self._aspect_ratio = self._pixmap.width() / self._pixmap.height()
        self._scaletofit()

        self.resizeEvent = self._on_resize

    @Slot()
    def message(self, msg):
        self._ui.msglabel.setText(msg)

    def _scaletofit(self):
        desired_width = int(self.width() * self._icon_width)
        max_height = int((self.height() - 2 * self._ui.verticalSpacer.sizeHint().height()) * self._max_icon_height)
        new_height = min(desired_width / self._aspect_ratio, max_height)
        pm = self._pixmap.scaled(desired_width, new_height, aspectMode=Qt.KeepAspectRatio, mode=Qt.SmoothTransformation)
        self._ui.iconlabel.setPixmap(pm)

    def _on_resize(self, event):
        self._scaletofit()
