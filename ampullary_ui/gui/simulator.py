import logging
import numpy as np
import pandas as pd

from pathlib import Path

from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtGui import QPixmap
from PySide6.QtCore import QLocale, QRunnable, Slot, QThreadPool

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

from ampullary_ui.ui.simulator_ui import Ui_Simulator
from ampullary_ui.utils import get_outputfolder, save_data, save_features, save_figure
from ampullary_ui.signals import SimulatorSignals
from ampullary_ui.plotting.plot_cell import plot_cell


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
        self._results = simulate_from_input_params(self._params, trials=5, baseline_duration=10.) # FIXME hardcode
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

        self._sim_thread = None
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

    def _setup_spinboxes(self):
        self.spinboxes = [getattr(self._ui, f"sc_doubleSpinBox_{i}") for i in range(1, 10)]
        self.spinbox_settings = [
            {"min": 0.05, "max": 40.0, "default": 21.46},
            {"min": 0.0,  "max": 3.0, "default": 2.47},
            {"min": 1.0,  "max": 100.0, "default": 33.25},
            {"min": 0.0,  "max": 5.0, "default": 3.14},
            {"min": -100.0,  "max": 0.0, "default": -15.62},
            {"min": 0.05, "max": 15.0, "default":7.32},
            {"min": 0.05, "max": 500.0, "default": 43.44},
            {"min": 0.0, "max": 10.0, "default": 5.58},
            {"min": 0.1, "max": 100.0, "default": 13.71}]
        for i, settings in enumerate(self.spinbox_settings, start=0):
            sb = self.spinboxes[i]
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
        self.placeholder_canvas = FigureCanvas(self._current_fig)  # current_fig now holds example_fig
        self.placeholder_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.plot_layout.addWidget(self.placeholder_canvas)

    def _load_example_fig(self):
        filepath = Path.cwd() / "examples" / "example_figures" / "base_example.pkl"
        example_base = pd.read_pickle(filepath)
        filepath = Path.cwd() / "examples" / "example_figures" / "stim_example.pkl"
        example_stim = pd.read_pickle(filepath)
        fig = plot_cell(example_base, example_stim)
        fig.text(0.5, 0.5, "EXAMPLE", fontsize=80, fontweight='bold', color='#44F9BD', alpha=0.6, ha='center', va='center', rotation=40, zorder=10)
        return fig   
 
    def _on_simulation_progress(self, msg, p):
        print("simulation progress", msg,  p)

    def _on_simulate(self):
        logging.info(f"Simulator: run simulation")

        self._ui.sc_btn_simulate.setEnabled(False)
        self._ui.sc_btn_reset.setEnabled(False)
        self._ui.sc_btn_save.setEnabled(False)
        self._ui.sc_back_to_main.setEnabled(False)
        self._ui.sc_btn_multi.setEnabled(False)
        params = [self.spinboxes[i].value() for i in range(0, 9)]

        self._sim_thread = SimulationThread(params)
        self._sim_thread._signals.progress.connect(self._on_simulation_progress)
        self._sim_thread._signals.finished.connect(self._on_simulation_finished)

        self.text_output.clear()
        self.text_output.insertPlainText("Simulating...\n")
        self.btn_simulate.setText("simulating…")
        self.main_controller.start_progress_animation()
        self._threadpool.start(self._sim_thread)
        self.progress.emit("simulating ...")

    def _on_reset(self):
        self.btn_reset.setEnabled(False)
        self.btn_save.setEnabled(False)
        self.name_edit.setText("simulation_001")
        for i, settings in enumerate(self.spinbox_settings):
            sb = self.spinboxes[i]
            sb.setValue(settings["default"])
        self.current_fig = self.example_fig
        self._show_simulation_figure()
        self.text_output.clear()
        self.text_output.insertPlainText('Just put in a set of parameters and press simulate!\n\nThe simulation includes 30 ms baseline activity and 100s white noise.') 
        self.progress.emit("")

    def _on_simulation_finished(self):
        logging.info("Simulator: simulation done...")

        self.main_controller.stop_progress_animation()
        self.results = self._sim_thread.results
        self._sim_thread = None
        # Create the matplotlib figure from your data
        self.progress.emit("Simulation done, plotting ...")
        self.text_output.insertPlainText('Simulation done, analyzing ...\n')

        fig = plot_cell(self.results.baseline_data, self.results.stimulus_data)
        self.current_fig = fig
        self._show_simulation_figure()
        self._ui.sc_btn_save.setEnabled(True)
        self._ui.sc_btn_simulate.setEnabled(True)
        self._ui.sc_btn_simulate.setText("simulate")
        self._ui.sc_btn_back.setEnabled(True)
        self._ui.sc_btn_multi.setEnabled(True)
        self._ui.sc_btn_reset.setEnabled(True)
        self._print_features()

    def _show_simulation_figure(self):
        # update figure   
        # Remove placeholder canvas if it exists
        if hasattr(self, 'placeholder_canvas') and self.placeholder_canvas:
            self.plot_layout.removeWidget(self.placeholder_canvas)
            self.placeholder_canvas.deleteLater()
            self.placeholder_canvas = None
        # Remove old simulation canvas if needed
        if hasattr(self, 'canvas') and self.canvas:
            self.plot_layout.removeWidget(self.canvas)
            self.canvas.deleteLater()
            self.canvas = None
        # Add matplotlib new canvas for updated simulation figure
        self.canvas = FigureCanvas(self.current_fig)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.plot_layout.addWidget(self.canvas)

    def _redraw_figure(self):
        if self.canvas:
            self.canvas.draw_idle()
            self.canvas.resize(self.canvas.size())

    def _print_features(self):
        self._text_output.insertPlainText('Your simulated cell has the following features:\n\n')
        label_width = max(len(s) for s in self.labels)
        for i, label in enumerate(self.labels):
            line = f'{label + ":":<{label_width + 1}} {np.round(self.results.features[i], 2)}\n'
            self._text_output.insertPlainText(line)

    def _on_save(self):
        logging.info("Simulator: saving results...")
        if self.results is None:
            self.text_output.insertPlainText('\nNothing to save\n')
            logging.debug("Simulator: no results, there is nothing to save")
            return
        output_folder = get_outputfolder()
        filename = self.name_edit.text().strip()

        if self.checkBox_data.isChecked():
            save_data(self.results.data, output_folder, filename)
            self.text_output.insertPlainText('\nData was saved\n')
        if self.checkBox_features.isChecked():
            save_features(self.results.features, output_folder, filename) 
            self.text_output.insertPlainText('\nFeatures were saved\n')
        if self.checkBox_figure.isChecked():
            if hasattr(self, 'current_fig'):
                save_figure(self.current_fig, output_folder, filename)
                self.text_output.insertPlainText('\nFigure was saved\n')
            else:
                self.text_output.insertPlainText('\nNo figure to save\n')
