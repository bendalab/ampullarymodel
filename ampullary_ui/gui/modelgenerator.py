import logging
import numpy as np

from PySide6.QtWidgets import QWidget, QSizePolicy, QMessageBox
from PySide6.QtCore import QLocale, QRunnable, Slot, QThreadPool, Signal, QSettings
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

from ampullary_ui.ui import Ui_ModelGenerator
from ampullary_ui.utils import get_outputfolder, save_data, save_features, save_params, load_labels
from ampullary_ui.signals import SimulatorSignals
from ampullary_ui.plotting.plot_cell import plot_cell
from ampullary_ui.simulation.helper import SimulationResult, simulate_from_input_params, create_cell_from_input_features, load_posterior


class SimulationThread(QRunnable):

    def __init__(self, params):
        super().__init__()
        self._params = params
        self._signals = SimulatorSignals()
        self._results = None

    @Slot()
    def run(self):
        self._signals.progress.emit("Running simulation ... ", 0.2)
        self._results = simulate_from_input_params(self._params, trials=5, baseline_duration=10.) # FIXME hardcode
        self._signals.progress.emit("...done", 1.0)
        self._signals.finished.emit(True)

    @property
    def signals(self):
        return self._signals

    @property
    def results(self) -> SimulationResult:
        return self._results


class GenerationThread(QRunnable):

    def __init__(self, features, posterior):
        super().__init__()
        self._features = features
        self._posterior = posterior
        self._signals = SimulatorSignals()
        self._results = None

    @Slot()
    def run(self):
        self._signals.progress.emit("Running simulation ... ", 0.2)
        self._results = create_cell_from_input_features(self._features, self._posterior)
        self._signals.progress.emit("...done", 1.0)
        self._signals.finished.emit(True)

    @property
    def signals(self):
        return self._signals

    @property
    def results(self):
        return self._results


class Modelgenerator(QWidget):
    """
    Generate model from feature set
    Simulate with this model to estimate model fit
    """
    simulating = Signal(str)
    simulation_done = Signal(str)
    generating = Signal(str)
    generating_done = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ui = Ui_ModelGenerator()
        self._ui.setupUi(self)
        self._qsettings = QSettings()
        self._threadpool = QThreadPool()
        self._sim_thread = None
        self._gen_thread = None

        self._placeholder_canvas = None
        self._canvas = None

        labels = load_labels()
        self._parameter_labels = labels['parameter_labels_casual']
        self._feature_labels = labels['feature_labels_casual']
        self._posterior = load_posterior(self._qsettings.value("model/posterior", ""))
        if self._posterior is None:
            QMessageBox.critical("Posterior file is missing!", "Could not locate or load the posterior file! Recheck the model settings.")
        self._model_params = None
        self._features = None
        self._simulation_results = None
        self._spinbox_settings = None
        self._spinboxes = [getattr(self._ui, f"doubleSpinBox_{i}") for i in range(1, len(self._feature_labels) + 1)]

        self._text_output = self._ui.text_output
        self._plot_container = self._ui.figure
        self._save_params_btn = self._ui.btn_save_model
        self._reset_btn = self._ui.btn_reset
        self._save_data_btn = self._ui.btn_save
        self._name_edit = self._ui.name_edit
        self._simulate_btn = self._ui.btn_simulate
        self._generate_btn = self._ui.btn_generate
        self._save_data_checkbox = self._ui.checkBox_data
        self._save_features_checkbox = self._ui.checkBox_features

        self._setup_spinboxes()
        self._setup_defaults()

        self._current_fig = None
        self._example_fig = None
        self._setup_placeholder_plot()

        self._generate_btn.clicked.connect(self._on_generate)
        self._reset_btn.clicked.connect(self._on_reset)
        self._simulate_btn.clicked.connect(self._on_simulate)
        self._save_params_btn.clicked.connect(self._on_save_params)
        self._save_data_btn.clicked.connect(self._on_save_data)

    def update(self):
        self._posterior = load_posterior(self._qsettings.value("model/posterior", ""))
        self._setup_defaults()

    def _setup_spinboxes(self):
        self._spinbox_settings = [
            {"min": 30.0, "max": 250.0, "default": 123.27},
            {"min": 0.0, "max": 4.67, "default": 0.04},
            {"min": -0.94, "max": 0.99, "default": -0.18},
            {"min": 0.0, "max": 600.0, "default": 20.82},
            {"min": 0.02, "max": 1.0, "default": 0.78},
            {"min": 0.06, "max": 1.0, "default":  0.93},
            {"min": 0.03, "max": 0.98, "default":  0.04},
            {"min": 0.0, "max": 148.93, "default":  12.21},
            {"min": 03.66, "max": 148.93, "default":  47.61},
            {"min": 0.0, "max": 26177.93, "default":  62.66},
            {"min": 0.0, "max": 38850.74, "default":  137.97},
            {"min": 0.0, "max": 45872.02, "default":  166.75},
            {"min": 0.0, "max": 1336.96, "default":  62.56},
            {"min": 0.0, "max": 2146.2, "default":  36.63},
            {"min": 0.0, "max": 74.46, "default": 10.99},
            {"min": 0.0, "max": 148.93, "default":  21.97},
            {"min": 0.0, "max": 148.93, "default":  48.83}]
        steps = np.zeros(len(self._spinbox_settings))
        for k in [1,2] + list(range(4, 7)):
            steps[k] = 0.01
        for k in [0, 3] + list(range(7, 16)):
            steps[k] = 1.0
        for i, settings in enumerate(self._spinbox_settings, start=0):
            sb = self._spinboxes[i]
            if sb is not None:
                sb.setMinimum(settings["min"])
                sb.setMaximum(settings["max"])
                sb.setValue(settings["default"])
                sb.setDecimals(2)
                sb.setSingleStep(steps[i])
                # Use a point as decimal separator
                sb.setLocale(QLocale(QLocale.C))

    def _setup_defaults(self):
        # set other defaults
        self._save_params_btn.setEnabled(False)
        self._reset_btn.setEnabled(False)
        self._simulate_btn.setEnabled(False)
        self._save_data_btn.setEnabled(False)
        self._name_edit.setText("model_001")
        self._save_data_checkbox.setChecked(True)
        self._save_features_checkbox.setChecked(False)
        self._generate_btn.setEnabled(self._posterior is not None) 

    def _setup_placeholder_plot(self):
        plot_layout = self._plot_container.layout()
        # Create a matplotlib canvas for the example figure placeholder
        self._placeholder_canvas = FigureCanvas(self._current_fig)  # current_fig now holds example_fig
        self._placeholder_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        plot_layout.addWidget(self._placeholder_canvas)

    def _show_simulation_figure(self):
        plot_layout = self._plot_container.layout()
        if hasattr(self, 'placeholder_canvas') and self._placeholder_canvas:
            plot_layout.removeWidget(self._placeholder_canvas)
            self._placeholder_canvas.deleteLater()
            self._placeholder_canvas = None

        if hasattr(self, 'canvas') and self._canvas:
            plot_layout.removeWidget(self._canvas)
            self._canvas.deleteLater()
            self._canvas = None

        self._canvas = FigureCanvas(self._current_fig)
        self._canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        plot_layout.addWidget(self._canvas)

    def redraw_figure(self):
        if self._canvas:
            self._canvas.draw_idle()
            self._canvas.resize(self._canvas.size())

    def _on_reset(self):
        self._reset_btn.setEnabled(False)
        self._simulate_btn.setEnabled(False)
        self._save_params_btn.setEnabled(False)
        self._save_data_btn.setEnabled(False)
        self._name_edit.setText("model_001")
        self._save_data_checkbox.setChecked(True)
        self._save_features_checkbox.setChecked(False)
        for i, settings in enumerate(self._spinbox_settings):
            sb = self._spinboxes[i]
            sb.setValue(settings["default"])
        self._current_fig = self._example_fig
        self.show_simulation_figure()
        self.text_output.clear()
        self.text_output.insertPlainText('Describe the cell you want to model by the offered features. A best-guess model that will generate your feature set will be proposed. You can immediately check how well the model fits be using it to simulate data and compare the simulated features with your input.')

    def _on_generate(self):
        logging.info("Modelgenerator: model generation running...")
        self.generating.emit("Generating model ...")
        self._generate_btn.setEnabled(False)
        self._generate_btn.setText("generating…")

        self._features = [spinbox.value() for spinbox in self._spinboxes]
        self._text_output.clear()
        self._text_output.insertPlainText("Computing MAP model from posterior...\n")

        self._gen_thread = GenerationThread(self._features, self._posterior)
        self._gen_thread.signals.progress.connect(self._on_generation_progress)
        self._gen_thread.signals.finished.connect(self._on_generation_finished)
        self._threadpool.start(self._gen_thread)

    def _on_generation_progress(self, msg, p):
        print("model generation progress", msg, p)

    def _on_generation_finished(self):
        logging.info("Modelgenerator: model generation done...")
        self.generating_done.emit("Model generation done!")

        self._model_params = self._gen_thread.results

        self._save_params_btn.setEnabled(True)
        self._reset_btn.setEnabled(True)
        self._simulate_btn.setEnabled(True)
        self._generate_btn.setEnabled(True)
        self._generate_btn.setText("generate")
        self._gen_thread = None
        self._print_params()

    def _on_simulate(self):
        logging.info("Simulator: run simulation")
        self.simulating.emit("Running simulation...")
        self._simulate_btn.setEnabled(False)
        self._reset_btn.setEnabled(False)
        self._save_data_btn.setEnabled(False)
        self._save_params_btn.setEnabled(False)

        self._sim_thread = SimulationThread(self._model_params)
        self._sim_thread.signals.progress.connect(self._on_simulation_progress)
        self._sim_thread.signals.finished.connect(self._on_simulation_finished)

        self._text_output.clear()
        self._text_output.insertPlainText("Simulating...\n")
        self._simulate_btn.setText("simulating…")

        self._threadpool.start(self._sim_thread)
        self.simulating.emit("simulating ...")

    def _on_simulation_progress(self, msg, p):
        print("simulation progress", msg, p)

    def _on_simulation_finished(self):
        logging.info("Modelgenerator: simulation done...")
        self.simulation_done.emit("Simulation done!")

        self._simulation_results = self._sim_thread.results

        fig = plot_cell(self._simulation_results.baseline_data,
                        self._simulation_results.stimulus_data)
        self._current_fig = fig

        self._show_simulation_figure()
        self._save_data_btn.setEnabled(True)
        self._simulate_btn.setEnabled(True)
        self._simulate_btn.setText("simulate")
        self._generate_btn.setEnabled(True)
        self._reset_btn.setEnabled(True)
        self._save_params_btn.setEnabled(True)
        self._text_output.insertPlainText(' simulation finished\n')
        self._sim_thread = None
        self._print_feature_comparison()

    def _print_params(self):
        self._text_output.clear()
        self._text_output.insertPlainText('Your model has the following parameters:\n\n')
        label_width = max(len(s) for s in self._parameter_labels)
        for i, label in enumerate(self._parameter_labels):
            line = f'{label + ":":<{label_width + 1}} {np.round(self._model_params[i], 2)}\n'
            self._text_output.insertPlainText(line)

    def _print_feature_comparison(self):
        self._text_output.insertPlainText('\nYour simulated cell has the following features:\n')
        label_width = max(len(s) for s in self._feature_labels)
        f_s =  ["%.2f" % number for number in self._features]
        f_width = max(len(f) for f in f_s)
        for i, label in enumerate(self._feature_labels):
            line = f'{label + ":":<{label_width + 1}} --> wanted: {np.round(self._features[i], 2):<{f_width + 1}} --> got: {np.round(self._simulation_results.features[i], 2)}\n'
            self._text_output.insertPlainText(line)

    def _on_save_params(self):
        folder = get_outputfolder()
        filename = self._name_edit.text().strip()

        if self._model_params is None:
            self._text_output.insertPlainText('\nNothing to save\n')
            return

        save_params(self._model_params, folder, filename)
        self._text_output.insertPlainText('\nParameter were saved\n')

    def _on_save_data(self):
        folder = get_outputfolder()
        filename = self._name_edit.text().strip()

        if self._simulation_results is None:
            self._text_output.insertPlainText('\nNothing to save\n')
            return
        if self._save_data_checkbox.isChecked():
            save_data(self._simulation_results.data, folder, filename)
            self._text_output.insertPlainText('\nData was saved\n')
        if self._save_features_checkbox.isChecked():
            save_features(self.results.features, folder, filename) 
            self._text_output.insertPlainText('\nFeatures were saved\n')
