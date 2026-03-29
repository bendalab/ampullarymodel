import logging
import numpy as np
from pathlib import Path

from PySide6.QtWidgets import QDoubleSpinBox, QSizePolicy, QFrame, QWidget, QFileDialog
from PySide6.QtCore import Signal, QLocale, QRunnable, Slot, QThreadPool, QSettings
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

from ampullary_ui.utils.saving_helper import save_data, save_features, save_figure, get_outputfolder
from ampullary_ui.plotting.plot_cell import plot_cell
from ampullary_ui.signals import SimulatorSignals

from IPython import embed
logging.debug("Imports done!")

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
    progress = Signal(str)

    def __init__(self, main_controller, feature_labels, parent=None):
        super().__init__(parent)
        logging.info("Simulator: init")
        self.main_controller = main_controller
        self.window = self.main_controller._window
        self.example_fig = self.main_controller._example_fig
        self.current_fig = self.example_fig
        self.results = None
        self.canvas = None
        self.labels = feature_labels

        self._sim_thread = None
        self._threadpool = QThreadPool()

        self._find_widgets()
        self._setup_spinboxes()
        self._setup_defaults()
        self._setup_placeholder_plot()
        self._connect_signals()
        self.progress.emit("Simulator initialized...")

    def _find_widgets(self):
        # initialization and setup
        self.btn_simulate = self.window.sc_btn_simulate
        self.btn_save = self.window.sc_btn_save
        self.btn_reset = self.window.sc_btn_reset
        self.text_output = self.window.sc_text_output
        self.name_edit = self.window.sc_input_name
        self.checkBox_data = self.window.sc_checkBox_data
        self.checkBox_features = self.window.sc_checkBox_features
        self.checkBox_figure = self.window.sc_checkBox_figure
        self.btn_back = self.window.sc_back_to_main
        self.btn_multi = self.window.sc_table_version
        self.plot_container = self.window.findChild(QFrame, "sc_figure")
        self.spinboxes = [
            self.window.findChild(QDoubleSpinBox, f"sc_doubleSpinBox_{i}")
            for i in range(1, 10)]

    def _setup_spinboxes(self):
        # set spinbox defaults
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
        # set other defaults
        self.btn_simulate.setEnabled(True)
        self.btn_save.setEnabled(False)
        self.btn_reset.setEnabled(False)
        self.name_edit.setText("simulation_001")
        self.checkBox_data.setChecked(True)
        self.checkBox_features.setChecked(False)
        self.checkBox_figure.setChecked(False)

    def _setup_placeholder_plot(self):
        self.plot_layout = self.plot_container.layout()
        self.placeholder_canvas = FigureCanvas(self.current_fig)  # current_fig now holds example_fig
        self.placeholder_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.plot_layout.addWidget(self.placeholder_canvas)

    def _connect_signals(self):
        self.btn_simulate.clicked.connect(self._on_simulate)
        self.btn_reset.clicked.connect(self._on_reset)
        self.btn_save.clicked.connect(self._on_save)

    def _on_simulation_progress(self, msg, p):
        print("simulation progress", msg,  p)

    def _on_simulate(self):
        logging.info(f"Simulator: run simulation")

        self.btn_simulate.setEnabled(False)
        self.btn_reset.setEnabled(False)
        self.btn_save.setEnabled(False)
        self.btn_back.setEnabled(False)
        self.btn_multi.setEnabled(False)
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
        self.btn_save.setEnabled(True)
        self.btn_simulate.setEnabled(True)
        self.btn_simulate.setText("simulate")
        self.btn_back.setEnabled(True)
        self.btn_multi.setEnabled(True)
        self.btn_reset.setEnabled(True)
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
        # print the features into the window
        self.text_output.insertPlainText('Your simulated cell has the following features:\n\n')
        label_width = max(len(s) for s in self.labels)
        for i, label in enumerate(self.labels):
            line = f'{label + ":":<{label_width + 1}} {np.round(self.results.features[i], 2)}\n'
            self.text_output.insertPlainText(line)

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
