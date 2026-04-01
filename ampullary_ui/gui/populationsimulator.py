import logging
import numpy as np
from pathlib import Path

from PySide6.QtWidgets import QDoubleSpinBox, QSizePolicy, QFrame, QWidget, QFileDialog
from PySide6.QtCore import Signal, QLocale, QRunnable, Slot, QThreadPool, QSettings, QThread
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

from ampullary_ui.ui.populationsimulator_ui import Ui_PopulationSimulator
from ampullary_ui.utils import save_data, save_features, save_figure, read_output_folder
from ampullary_ui.plotting.plot_cell import plot_cell
from ampullary_ui.signals import SimulatorSignals
from ampullary_ui.computations.controller_functions import simulate_from_input_params


class SimulationThreadMulti(QThread):
    finished = Signal(object)   # emits results when done
    progress = Signal(str)      # emits progress messages

    def __init__(self, params, save_raw, calc_feats, input_dir, output_dir):
        super().__init__()
        self.params = params
        self.save_raw = save_raw
        self.calc_feats = calc_feats
        self.output_dir = output_dir
        self.input_dir = input_dir
        self._is_running = True
        self.current_proc = None
        self.result_queue = None
        self.progress_queue = None

    def stop(self):
        self._is_running = False
        if self.current_proc and self.current_proc.is_alive():
            self.progress.emit("Terminating current subprocess...")
            self.current_proc.terminate()
            self.current_proc.join()

    def run(self):
        # load stimulus and stim length here
        collect_results = []
        stimulus, stim_data, stimulus_length = get_stimulus_and_data()
        # Create subfolder for raw data inside output_dir
        filename = self.input_dir.stem
        raw_data_dir = Path(self.output_dir) / f"{filename}_simulation_raw_data"
        raw_data_dir.mkdir(exist_ok=True, parents=True)
        total_rows = sum(package.shape[0] for _, package in self.params)

        for start_idx, package in self.params:
            if not self._is_running:
                self.progress.emit("Simulation cancelled by user.")
                break

            end_idx = start_idx + len(package)
            self.progress.emit(
                f"Simulating cells {start_idx+1} to {end_idx} of {total_rows}")

            self.result_queue = multiprocessing.Queue()
            self.progress_queue = multiprocessing.Queue()
            self.current_proc = multiprocessing.Process(target=worker_function_simulate_multi, 
                                                        args=(start_idx, package, stimulus, stim_data, stimulus_length, 
                                                              self.result_queue, self.progress_queue, 
                                                              self.save_raw, self.calc_feats, raw_data_dir))
            self.current_proc.start()
            self.current_proc.join()

            # Try to get result if any
            try:
                result = self.result_queue.get_nowait()
                if result is None:
                    collect_results.append(np.full((len(package), 17), np.nan))
                    saved_flag = False
                else:
                    collect_results.append(result['features'])
                    saved_flag = result['saved_flag']
            except Exception:
                collect_results.append(np.full((len(package), 17), np.nan))
                saved_flag = False
        if saved_flag:
            self.progress.emit(f"Simulation data saved under {self.output_dir}")
        results = np.vstack(collect_results)
        self.finished.emit(results)


class PopulationSimulator(QWidget):
    simulating = Signal(str)
    simulation_done = Signal(str)


    def __init__(self, parent=None):
        super().__init__(parent)

        self._ui = Ui_PopulationSimulator()
        self._ui.setupUi(self)

        self.results = None
        self.save_flag = True
        self.sim_thread = None

        self._run_btn = self._ui.run_btn
        self._cancel_btn = self._ui.cancel_btn
        self._input_path_edit = self._ui.input_path_edit
        self._output_path_edit = self._ui.output_path_edit
        self._open_input_btn = self._ui.input_path_btn
        self._open_output_btn = self._ui.output_path_btn
        self._save_data_checkbox = self._ui.save_data_checkbox
        self._compute_features_checkbox = self._ui.compute_features_checkbox
        self._text_output = self._ui.text_output
        self._info_text = self._ui.info_text

        self._setup_defaults()

        self._open_input_btn.clicked.connect(self._on_open_input)
        self._open_output_btn.clicked.connect(self._on_open_output)

    def _setup_defaults(self):
        self._cancel_btn.setEnabled(False)
        self._save_data_checkbox.setChecked(True)
        self._compute_features_checkbox.setChecked(True)
        self._input_path_edit.setText("examples/example_parameters.csv")
        self._output_path_edit.setText(str(read_output_folder()))
        self._info_text.setOpenExternalLinks(False)
        self._info_text.setOpenLinks(False)

    def _on_open_input(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select CSV File", "", "CSV Files (*.csv)"
        )
        if file_path:
            self._input_path_edit.setText(file_path)

    def _on_open_output(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", self._output_path_edit.text()
        )
        if dir_path:
            self._output_path_edit.setText(dir_path)
