import logging
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Signal, Qt

from ampullary_ui.ui import Ui_StartPage
from ampullary_ui.utils import Tool

class StartPage(QWidget):
    tool_selection = Signal(Tool)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.ui = Ui_StartPage()
        self.ui.setupUi(self)
        self._icon_width = 0.8 / 3
        self._icon_maxheight = 500
        self._pm1 = QPixmap(":/examples/eqn")
        self._pm2 = QPixmap(":/examples/get_model")
        self._pm3 = QPixmap(":/examples/table")
        for pixmap, label in zip([self._pm1, self._pm2, self._pm3],
                                 [self.ui.picture_1, self.ui.picture_2, self.ui.picture_3]):
            self._scaletofit(pixmap, label)

        self.resizeEvent = self._on_resize

        self.ui.simulatorbtn.clicked.connect(self._on_simulator)
        self.ui.generatorbtn.clicked.connect(self._on_generator)
        self.ui.catalogbtn.clicked.connect(self._on_catalog)

    def _on_simulator(self):
        self.tool_selection.emit(Tool.SIMULATOR)

    def _on_generator(self):
        self.tool_selection.emit(Tool.MODELGENERATOR)

    def _on_catalog(self):
        self.tool_selection.emit(Tool.MODELCATALOG)

    def _scaletofit(self, pixmap, label):
        aspect_ratio = pixmap.width() / pixmap.height()
        desired_width = int(self.width() * self._icon_width)
        new_height = min(desired_width / aspect_ratio, self._icon_maxheight)
        pm = pixmap.scaled(desired_width, new_height, aspectMode=Qt.KeepAspectRatio, mode=Qt.SmoothTransformation)
        label.setPixmap(pm)

    def _on_resize(self, event):
        for pixmap, label in zip([self._pm1, self._pm2, self._pm3],
                                 [self.ui.picture_1, self.ui.picture_2, self.ui.picture_3]):
            self._scaletofit(pixmap, label)
        super().resizeEvent(event)
