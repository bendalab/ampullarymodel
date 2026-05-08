import logging
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout, QWidget, QHBoxLayout
from PySide6.QtCore import Qt, QSettings

from ampullary_ui.gui.modelsettings import ModelSettings


class ModelSettingsDialog(QDialog):

    def __init__(self, parent=None) -> None:
        super().__init__(parent=parent)
        self.setModal(True)
        self.setLayout(QVBoxLayout())
        self._bbox = QDialogButtonBox(standardButtons=QDialogButtonBox.StandardButton.Ok |
                                                QDialogButtonBox.StandardButton.Cancel)
        self._bbox.accepted.connect(self._on_accept)
        self._bbox.rejected.connect(self._on_reject)

        self._settings = QSettings()
        width = int(self._settings.value("msettings/width", 640))
        height = int(self._settings.value("msettings/height", 480))
        x = int(self._settings.value("msettings/pos_x", 100))
        y = int(self._settings.value("msettings/pos_y", 100))

        self._modelsettings = ModelSettings(self)
        self.layout().addWidget(self._modelsettings)
        self.layout().addWidget(self._bbox)

        self.setMinimumSize(640, 480)
        self.resize(width, height)
        self.move(x, y)
        self.finished.connect(self.on_finished)

        self._modelsettings.busy.connect(self._is_busy)
        self._modelsettings.done.connect(self._is_done)

    def _is_busy(self):
        ok_button = self._bbox.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button is not None:
            ok_button.setEnabled(False)

    def _is_done(self):
        ok_button = self._bbox.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button is not None:
            ok_button.setEnabled(True)

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
        self._modelsettings.cancel_download()
        self.reject()

    def closeEvent(self, event):
        self._modelsettings.cancel_download()
        super().closeEvent(event)
