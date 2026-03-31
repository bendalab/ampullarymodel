import logging
import argparse
import ampullary_ui.info as info

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings

import ampullary_ui.resources_rc
from ampullary_ui.utils import load_style
from ampullary_ui.gui import MainWindow

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
    parser = create_parser()
    args = parser.parse_args()
    args.loglevel = log_levels[args.loglevel.lower() if args.loglevel.lower() in log_levels else "info"]

    main(args)