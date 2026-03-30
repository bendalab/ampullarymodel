import logging
import argparse
import ampullary_ui.info as info

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings

import ampullary_ui.resources_rc
from ampullary_ui.utils import load_style
from ampullary_ui.gui import MainWindow


def main():
    app = QApplication()
    app.setApplicationName(info.application_name)
    app.setApplicationVersion(str(info.application_version))
    app.setOrganizationDomain(info.organization_name)
    app.setStyle("Fusion")
    style = load_style()
    app.setStyleSheet(style)

    settings = QSettings()
    width = int(settings.value("app/width", 1024))
    height = int(settings.value("app/height", 768))
    x = int(settings.value("app/pos_x", 100))
    y = int(settings.value("app/pos_y", 100))

    window = MainWindow()
    window.show()
    window.setWindowTitle("Ampullary Simulator")
    window.setGeometry(x, y, width, height)
    window.setMinimumWidth(800)
    window.setMinimumHeight(600)
    window.resize(width, height)
    window.move(x, y)
    window.show()
    app.exec()

    logging.info("updating settings %s", window.geometry())
    pos = window.pos()
    settings.setValue("app/width", window.width())
    settings.setValue("app/height", window.height())
    settings.setValue("app/pos_x", pos.x())
    settings.setValue("app/pos_y", pos.y())

if __name__ == "__main__":
    main()
