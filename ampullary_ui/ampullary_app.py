import logging
import argparse

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings

import ampullary_ui.resources_rc
from ampullary_ui.controllers.main_controller import MainController
from ampullary_ui.controllers.ui_loding_helper import load_ui
from ampullary_ui.utils import load_style
from ampullary_ui import info


logging.basicConfig(level=logging.INFO, force=True)
log_levels = {"critical": logging.CRITICAL, "error": logging.ERROR,
              "warning":logging.WARNING, "info":logging.INFO,
              "debug":logging.DEBUG}


def set_logging(loglevel):
    logging.basicConfig(level=loglevel, force=True)


def create_parser():
    parser = argparse.ArgumentParser(description="AmpullaryUi. Tool for creating models of ampullary afferents")
    parser.add_argument("-ll", "--loglevel", type=str, default="INFO",
                        help=f"The log level that should be used. Valid levels are {[str(k) for k in log_levels.keys()]}")
    return parser

def main(args=None):
    if args is None:
        parser = create_parser()
        args = parser.parse_args()
        args.loglevel = log_levels[args.loglevel.lower() if args.loglevel.lower() in log_levels else "info"]
    set_logging(args.loglevel)
    logging.info("Starting Ampullary-GUI")
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
    window = load_ui(":/ui/gui")

    controller = MainController(window)
    window.setGeometry(100, 100, 1024, 768)
    window.setWindowTitle("AmpullaryUi")
    window.setMinimumWidth(1024)
    window.setMinimumHeight(768)
    window.resize(width, height)
    window.move(x, y)
    window.show()
    app.exec()

    logging.info(f"updating settings {window.geometry()}")
    pos = window.pos()
    settings.setValue("app/width", window.width())
    settings.setValue("app/height", window.height())
    settings.setValue("app/pos_x", pos.x())
    settings.setValue("app/pos_y", pos.y())


if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()
    args.loglevel = log_levels[args.loglevel.lower() if args.loglevel.lower() in log_levels else "info"]

    main(args)

"""   
Questions for Jan to tool:

- setup placeholder, show figure, → should I share methods, and if so, how?
- how to handle explanation, info page? More useful figures? Just paper ref? pillte pictorgams include?
- do I need to somehow incorporate table convert or is line in terminal fine? (finish first)
- do we have a windows laptop around to try this out?
- can I ask the other people for feedback / finding bugs?
- labeling: B1 B2 ETC include or not (currently inconsistent)
- something I noted on the TEX
"""