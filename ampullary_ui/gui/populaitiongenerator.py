import logging
import numpy as np

from PySide6.QtWidgets import  QWidget, QFileDialog
from PySide6.QtCore import Signal, QThread

from ampullary_ui.ui.populationgenerator_ui import Ui_PopulationGenerator
from ampullary_ui.utils import read_output_folder


class GenerationThreadMulti(QThread):
    finished = Signal(object)   # emits results when done
    progress = Signal(str)      # emits progress messages

    def __init__(self, params):
        super().__init__()
        self.params = params
        self._is_running = True
        self.maxtime = 1 * 60  # seconds
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
        posterior = load_posterior()
        rel_stats = prepare_feature_inputs(self.params)
        results = np.full((len(rel_stats), 9), np.nan)

        for i, row in enumerate(rel_stats):
            if not self._is_running:
                self.progress.emit("Computing cancelled by user.")
                break

            self.progress.emit(f'Computing MAP model for cell {i+1} of {len(rel_stats)}')
            self.result_queue = multiprocessing.Queue()
            self.progress_queue = multiprocessing.Queue()
            self.current_proc = multiprocessing.Process(target=worker_function_generate_multi, args=(row, posterior, self.result_queue, self.progress_queue))
            self.current_proc.start()
            elapsed = 0
            poll_interval = 0.1  # seconds
            while self.current_proc.is_alive() and self._is_running and elapsed < self.maxtime:
                try:
                    while True:
                        msg = self.progress_queue.get_nowait()
                        self.progress.emit(msg)
                except Exception:
                    pass

                self.current_proc.join(timeout=poll_interval)
                elapsed += poll_interval

            # If we exited because time expired or cancellation requested
            if self.current_proc.is_alive():
                self.progress.emit(f"Cell {i+1} timed out or cancelled. Terminating...")
                self.current_proc.terminate()
                self.current_proc.join()

            # Try to get result if any
            try:
                result = self.result_queue.get_nowait()
                if result is None:
                    results[i] = np.full((9,), np.nan)
                else:
                    results[i] = result
            except Exception:
                results[i] = np.full((9,), np.nan)

        self.finished.emit(results)

class PopulationGenerator(QWidget):
    simulating = Signal(str)
    simulation_done = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._ui = Ui_PopulationGenerator()
        self._ui.setupUi(self)

        self._results = None
        self._save_flag = True
        self._sim_thread = None  # Initialize thread variable

        self._run_btn = self._ui.btn_run
        self._cancel_btn = self._ui.btn_cancel
        self._input_path_edit = self._ui.input_path
        self._output_path_edit = self._ui.output_path
        self._text_output = self._ui.tc_text_output
        self._open_input_btn = self._ui.open_input_btn
        self._open_output_btn = self._ui.open_output_btn
        self._info_text = self._ui.tc_info

        self._open_input_btn.clicked.connect(self._on_open_input)
        self._open_output_btn.clicked.connect(self._on_open_output)
        self._run_btn.clicked.connect(self._on_run)
        self._info_text.anchorClicked.connect(self.open_example)

        self.setup_defaults()

    def setup_defaults(self):
        self._cancel_btn.setEnabled(False)
        self._input_path_edit.setText("examples/example_features.csv")
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

    def _on_run(self):
        pass

    def open_example(self):
        pass