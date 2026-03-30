import logging
import argparse
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import QSettings
from PySide6.QtUiTools import QUiLoader


import sys

from ampullary_ui.ui import Ui_MainWindow


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, *args, obj=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)


app = QApplication(sys.argv)

window = MainWindow()
window.show()
app.exec()