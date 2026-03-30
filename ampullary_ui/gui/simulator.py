import logging
import numpy as np

from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Signal, QLocale, QRunnable, Slot, QThreadPool

from ampullary_ui.ui.simulator_ui import Ui_Simulator
from ampullary_ui.utils import get_outputfolder, save_data, save_features, save_figure


class SimulationThread(QRunnable):

    def __init__(self, params):
        super().__init__()
        self._params = params
        self._signals = SimulatorSignals()
        self._results = None

    @Slot()
    def run(self):
        self._signals.progress.emit("Imports ...", 0.1)
        from ampullary_ui.computations.controller_functions import (
            simulate_from_input_params
        )
        self._signals.progress.emit("Running simulation ... ", 0.2)
        self._results = simulate_from_input_params(self._params, trials=5, baseline_duration=10.)
        self._signals.progress.emit("...done", 1.0)
        self._signals.finished.emit(True)

    @property
    def results(self):
        return self._results

class Simulator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._ui = Ui_Simulator()
        self._ui.setupUi(self)

    