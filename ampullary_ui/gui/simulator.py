import logging
import numpy as np
import pandas as pd

from pathlib import Path

from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtGui import QPixmap
from PySide6.QtCore import QLocale, QRunnable, Slot, QThreadPool, Signal

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

from ampullary_ui.ui.simulator_ui import Ui_Simulator
from ampullary_ui.utils import get_outputfolder, save_data, save_features, save_figure, load_labels
from ampullary_ui.signals import SimulatorSignals
from ampullary_ui.plotting.plot_cell import plot_cell
from ampullary_ui.computations.controller_functions import simulate_from_input_params


class SimulationThread(QRunnable):

    def __init__(self, params):
        super().__init__()
        self._params = params
        self._signals = SimulatorSignals()
        self._results = None

    @Slot()
    def run(self):
        self._signals.progress.emit("Imports ...", 0.1)
        self._signals.progress.emit("Running simulation ... ", 0.2)
        self._results = simulate_from_input_params(self._params, trials=5, baseline_duration=10.) # FIXME hardcode
        self._signals.progress.emit("...done", 1.0)
        self._signals.finished.emit(True)

    @property
    def signals(self):
        return self._signals

    @property
    def results(self):
        return self._results


class Simulator(QWidget):
    simulating = Signal(str)
    simulation_done = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._ui = Ui_Simulator()
        self._ui.setupUi(self)

        self._sim_thread = None
        self._placeholder_canvas = None
        self._canvas = None
        self._results = None
        self._spinbox_settings = None
        self._spinboxes = None
        self._labels = load_labels()['feature_labels_casual']
        self._threadpool = QThreadPool()
        self._text_output = self._ui.sc_text_output
        self._plot_container = self._ui.sc_figure
        self._ui.sc_equation.setPixmap(QPixmap(":/examples/eqn2"))
        self._setup_spinboxes()
        self._setup_defaults()

        self._example_fig = self._load_example_fig()
        self._current_fig = self._example_fig
        self._setup_placeholder_plot()
        self._ui.sc_btn_simulate.clicked.connect(self._on_simulate)
        self._ui.sc_btn_save.clicked.connect(self._on_save)
        self._ui.sc_btn_reset.clicked.connect(self._on_reset)

    def _setup_spinboxes(self):
        self._spinboxes = [getattr(self._ui, f"sc_doubleSpinBox_{i}") for i in range(1, 10)]
        self._spinbox_settings = [
            {"min": 0.05, "max": 40.0, "default": 21.46},
            {"min": 0.0,  "max": 3.0, "default": 2.47},
            {"min": 1.0,  "max": 100.0, "default": 33.25},
            {"min": 0.0,  "max": 5.0, "default": 3.14},
            {"min": -100.0,  "max": 0.0, "default": -15.62},
            {"min": 0.05, "max": 15.0, "default":7.32},
            {"min": 0.05, "max": 500.0, "default": 43.44},
            {"min": 0.0, "max": 10.0, "default": 5.58},
            {"min": 0.1, "max": 100.0, "default": 13.71}]
        for i, settings in enumerate(self._spinbox_settings, start=0):
            sb = self._spinboxes[i]
            if sb is not None:
                sb.setMinimum(settings["min"])
                sb.setMaximum(settings["max"])
                sb.setValue(settings["default"])
                sb.setDecimals(2)
                # Use a point as decimal separator
                sb.setLocale(QLocale(QLocale.C))

    def _setup_defaults(self):
        self._ui.sc_btn_simulate.setEnabled(True)
        self._ui.sc_btn_save.setEnabled(False)
        self._ui.sc_btn_reset.setEnabled(False)
        self._ui.sc_input_name.setText("simulation_001")  # FIXME hardcode?
        self._ui.sc_checkBox_data.setChecked(True)
        self._ui.sc_checkBox_features.setChecked(False)
        self._ui.sc_checkBox_figure.setChecked(False)

    def _setup_placeholder_plot(self):
        self.plot_layout = self._plot_container.layout()
        self._placeholder_canvas = FigureCanvas(self._current_fig)  # current_fig now holds example_fig
        self._placeholder_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.plot_layout.addWidget(self._placeholder_canvas)

    def _load_example_fig(self):
        filepath = Path.cwd() / "examples" / "example_figures" / "base_example.pkl"
        example_base = pd.read_pickle(filepath)
        filepath = Path.cwd() / "examples" / "example_figures" / "stim_example.pkl"
        example_stim = pd.read_pickle(filepath)
        fig = plot_cell(example_base, example_stim)
        fig.text(0.5, 0.5, "EXAMPLE", fontsize=80, fontweight='bold', color='#44F9BD',
                 alpha=0.6, ha='center', va='center', rotation=40, zorder=10)
        return fig

    def _on_simulation_progress(self, msg, p):
        print("simulation progress", msg,  p)

    def _on_simulate(self):
        logging.info("Simulator: run simulation")
        self.simulating.emit("Running simulation...")
        self._ui.sc_btn_simulate.setEnabled(False)
        self._ui.sc_btn_reset.setEnabled(False)
        self._ui.sc_btn_save.setEnabled(False)
        params = [self._spinboxes[i].value() for i in range(0, 9)]

        self._sim_thread = SimulationThread(params)
        self._sim_thread.signals.progress.connect(self._on_simulation_progress)
        self._sim_thread.signals.finished.connect(self._on_simulation_finished)

        self._text_output.clear()
        self._text_output.insertPlainText("Simulating...\n")
        self._ui.sc_btn_simulate.setText("simulating…")

        self._threadpool.start(self._sim_thread)
        self.simulating.emit("simulating ...")

    def _on_reset(self):
        # self.btn_reset.setEnabled(False)
        self._ui.sc_btn_save.setEnabled(False)
        self._ui.sc_btn_reset.setEnabled(False)
        self._ui.sc_input_name.setText("simulation_001")
        for i, settings in enumerate(self._spinbox_settings):
            sb = self._spinboxes[i]
            sb.setValue(settings["default"])
        self._current_fig = self._example_fig
        self._show_simulation_figure()
        self._text_output.clear()
        self._text_output.insertPlainText('Just put in a set of parameters and press simulate!\n\nThe simulation includes 30 ms baseline activity and 100s white noise.')
        self.progress.emit("")

    def _on_simulation_finished(self):
        logging.info("Simulator: simulation done...")
        self.simulation_done.emit("Simulation done!")

        self._results = self._sim_thread.results
        self._sim_thread = None
        # Create the matplotlib figure from your data
        self._text_output.insertPlainText('Simulation done, analyzing ...\n')

        fig = plot_cell(self._results.baseline_data, self._results.stimulus_data)
        self._current_fig = fig
        self._show_simulation_figure()
        self._ui.sc_btn_save.setEnabled(True)
        self._ui.sc_btn_simulate.setEnabled(True)
        self._ui.sc_btn_simulate.setText("simulate")
        self._ui.sc_btn_reset.setEnabled(True)

        self._print_features()

    def _show_simulation_figure(self):
        if hasattr(self, '_placeholder_canvas') and self._placeholder_canvas:
            self.plot_layout.removeWidget(self._placeholder_canvas)
            self._placeholder_canvas.deleteLater()
            self._placeholder_canvas = None

        if hasattr(self, '_canvas') and self._canvas:
            self.plot_layout.removeWidget(self._canvas)
            self._canvas.deleteLater()
            self._canvas = None

        self._canvas = FigureCanvas(self._current_fig)
        self._canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.plot_layout.addWidget(self._canvas)

    def _redraw_figure(self):
        if self._canvas:
            self._canvas.draw_idle()
            self._canvas.resize(self._canvas.size())

    def _print_features(self):
        self._text_output.insertPlainText('Your simulated cell has the following features:\n\n')
        label_width = max(len(s) for s in self._labels)
        for i, label in enumerate(self._labels):
            line = f'{label + ":":<{label_width + 1}} {np.round(self._results.features[i], 2)}\n'
            self._text_output.insertPlainText(line)

    def _on_save(self):
        logging.info("Simulator: saving results...")
        if self._results is None:
            self._text_output.insertPlainText('\nNothing to save\n')
            logging.debug("Simulator: no results, there is nothing to save")
            return
        output_folder = get_outputfolder()
        filename = self._ui.sc_input_name.text().strip()

        if self.checkBox_data.isChecked():
            save_data(self._results.data, output_folder, filename)
            self._text_output.insertPlainText('\nData was saved\n')
        if self.checkBox_features.isChecked():
            save_features(self._results.features, output_folder, filename) 
            self._text_output.insertPlainText('\nFeatures were saved\n')
        if self.checkBox_figure.isChecked():
            if hasattr(self, 'current_fig'):
                save_figure(self._current_fig, output_folder, filename)
                self._text_output.insertPlainText('\nFigure was saved\n')
            else:
                self._text_output.insertPlainText('\nNo figure to save\n')
