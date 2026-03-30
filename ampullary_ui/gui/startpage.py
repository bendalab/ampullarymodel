import logging
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Signal

from ampullary_ui.ui import Ui_StartPage
from ampullary_ui.utils import Tool

class StartPage(QWidget):
    tool_selection = Signal(Tool)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.ui = Ui_StartPage()
        self.ui.setupUi(self)
        # FIXME the aspect ratio is not the same as in the original
        self.ui.picture_1.setPixmap(QPixmap(":/examples/eqn"))
        self.ui.picture_2.setPixmap(QPixmap(":/examples/get_model"))
        self.ui.picture_3.setPixmap(QPixmap(":/examples/table"))
        # Set a fixed width for all pixmaps
        pixmap_width = int(0.8 * self.width() / 3)
        for picture in [self.ui.picture_1, self.ui.picture_2, self.ui.picture_3]:
            picture.setFixedWidth(pixmap_width)
            picture.setScaledContents(True)

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

    def _on_resize(self, event):
        """Handle window resize events."""
        pixmap_width = int(0.8 * self.width() / 3)
        for picture in [self.ui.picture_1, self.ui.picture_2, self.ui.picture_3]:
            picture.setFixedWidth(int(pixmap_width))
        super().resizeEvent(event)
