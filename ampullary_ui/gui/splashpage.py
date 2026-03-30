import logging
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Slot, Signal

from ampullary_ui.ui import Ui_LoadingSplash

class SplashPage(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)


        self._ui = Ui_LoadingSplash()
        self._ui.setupUi(self)
        self._ui.iconlabel.setPixmap(QPixmap(":/icons/icon"))
    

    @Slot()
    def message(self, msg):
        self._ui.msglabel.setText(msg)
