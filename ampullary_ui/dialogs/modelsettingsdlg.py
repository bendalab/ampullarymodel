import logging
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout, QWidget, QHBoxLayout
from PySide6.QtCore import Qt, QSettings

from ampullary_ui.gui.modelsettings import ModelSettings


class ModelSettingsDialog(QDialog):

    def __init__(self, parent=None) -> None:
        super().__init__(parent=parent)
        self.setModal(True)
        self.setLayout(QVBoxLayout())
        bbox = QDialogButtonBox(standardButtons=QDialogButtonBox.StandardButton.Ok |
                                                QDialogButtonBox.StandardButton.Cancel)
        bbox.accepted.connect(self._on_accept)
        bbox.rejected.connect(self._on_reject)

        self._settings = QSettings()
        width = int(self._settings.value("msettings/width", 640))
        height = int(self._settings.value("msettings/height", 480))
        x = int(self._settings.value("msettings/pos_x", 100))
        y = int(self._settings.value("msettings/pos_y", 100))

        self._modelsettings = ModelSettings(self)
        self.layout().addWidget(self._modelsettings)
        self.layout().addWidget(bbox)

        self.setMinimumSize(640, 480)
        self.resize(width, height)
        self.move(x, y)
        self.finished.connect(self.on_finished)

    def on_finished(self):
        print("on_finished!")
        self._settings.setValue("msettings/width", self.width())
        self._settings.setValue("msettings/height", self.height())
        self._settings.setValue("msettings/pos_x", self.x())
        self._settings.setValue("msettings/pos_y", self.y())

    def _on_accept(self):
        logging.info("modelsettingsdialog.on_accept!")
        if self._modelsettings.store_settings():
            self.accept()

    def _on_reject(self):
        logging.info("modelsettingsdialog.on_cancel!")
        self.reject()
