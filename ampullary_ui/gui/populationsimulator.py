import logging
import numpy as np
import pandas as pd
import multiprocessing

from pathlib import Path

from PySide6.QtWidgets import QWidget, QFileDialog
from PySide6.QtCore import Signal, QThread

from ampullary_ui.ui.populationsimulator_ui import Ui_PopulationSimulator
from ampullary_ui.computations.table_conversion_gui import package_parameters, worker_function_simulate_multi
from ampullary_ui.dialogs import CancelConfirmDialog
from ampullary_ui.utils import save_data, save_features, read_output_folder, save_features_table, load_gwnstimulus, modify_stimulus
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
        stim_data = load_gwnstimulus()
        stimulus = modify_stimulus(stim_data)

        # Create subfolder for raw data inside output_dir
        filename = self.input_dir.stem
        raw_data_dir = Path(self.output_dir) / f"{filename}_simulation_raw_data"
        raw_data_dir.mkdir(exist_ok=True, parents=True)
        total_rows = sum(package.shape[0] for _, package in self.params)

        for start_idx, package_params in self.params:
            if not self._is_running:
                self.progress.emit("Simulation cancelled by user.")
                break

            end_idx = start_idx + len(package_params)
            self.progress.emit(
                f"Simulating cells {start_idx+1} to {end_idx} of {total_rows}")

            self.result_queue = multiprocessing.Queue()
            self.progress_queue = multiprocessing.Queue()
            self.current_proc = multiprocessing.Process(target=worker_function_simulate_multi, 
                                                        args=(start_idx, package_params, stimulus, stim_data,
                                                              self.result_queue, self.progress_queue, 
                                                              self.save_raw, self.calc_feats, raw_data_dir))
            self.current_proc.start()
            self.current_proc.join()

            # Try to get result if any
            try:
                result = self.result_queue.get_nowait()
                if result is None:
                    collect_results.append(np.full((len(package_params), 17), np.nan))
                    saved_flag = False
                else:
                    collect_results.append(result['features'])
                    saved_flag = result['saved_flag']
            except Exception:
                collect_results.append(np.full((len(package_params), 17), np.nan))
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

        self._results = None
        self._save_flag = True
        self.sim_thread = None

        self._run_simulation_btn = self._ui.run_btn
        self._cancel_btn = self._ui.cancel_btn
        self._input_path_edit = self._ui.input_path_edit
        self._output_path_edit = self._ui.output_path_edit
        self._open_input_btn = self._ui.input_path_btn
        self._open_output_btn = self._ui.output_path_btn
        self._save_data_checkbox = self._ui.save_data_checkbox
        self._save_features_checkbox = self._ui.save_features_checkbox
        self._text_output = self._ui.text_output
        self._info_text = self._ui.info_text

        self._setup_defaults()

        self._open_input_btn.clicked.connect(self._on_open_input)
        self._open_output_btn.clicked.connect(self._on_open_output)
        self._run_simulation_btn.clicked.connect(self._on_run_simulation)
        self._cancel_btn.clicked.connect(self._on_cancel_simulation)

    def _setup_defaults(self):
        self._cancel_btn.setEnabled(False)
        self._save_data_checkbox.setChecked(True)
        self._save_features_checkbox.setChecked(True)
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

    def _on_run_simulation(self):
        logging.info("PopulationSimulator: run simulations")
        if hasattr(self, 'sim_thread') and self.sim_thread is not None and self.sim_thread.isRunning():
            self._text_output.appendPlainText("Please wait for current subprocess to be cancelled.")
            return

        input_path = Path(self._input_path_edit.text())
        if not input_path.exists():
            logging.info("PopulationSimulator: Input file %s does not exist!")
            self._text_output.appendPlainText("Input file does not exist, please re-check.")
            return

        output_path = Path(self._output_path_edit.text())
        if not output_path.exists():
            logging.info("PopulationSimulator: Output path %s does not exist!")
            self._text_output.appendPlainText("Output path does not exist, please re-check.")
            return

        self.simulating.emit("Running simulations")
        self._run_simulation_btn.setEnabled(False)
        self._run_simulation_btn.setText("running…")
        self._cancel_btn.setEnabled(True)

        parameters = pd.read_csv(input_path)
        params = package_parameters(parameters)
        save_raw = self._save_data_checkbox.isChecked()
        calc_feats = self._save_features_checkbox.isChecked()
        self._text_output.insertPlainText("\nSimulating in chunks of 100...\n")

        self.sim_thread = SimulationThreadMulti(params, save_raw, calc_feats, input_path, output_path)
        self.sim_thread.progress.connect(self._update_progress_text)
        self.sim_thread.finished.connect(self._on_simulations_finished)
        self.sim_thread.finished.connect(self.sim_thread.quit)  # Clean up thread when done
        self.sim_thread.finished.connect(self.sim_thread.deleteLater)
        self.sim_thread.start()

    def _on_cancel_simulation(self):
        if hasattr(self, 'sim_thread') and self.sim_thread is not None and self.sim_thread.isRunning():
            dlg = CancelConfirmDialog(self)
            result = dlg.exec()

            if result == 1:  # Save and Cancel
                self.sim_thread.stop()
                self._cancel_btn.setEnabled(False)
                self._run_simulation_btn.setEnabled(True)
                self._run_simulation_btn.setText("run")
                # saving handled in on_simulation_finished
            elif result == 2:  # Cancel without saving
                self._save_flag = False
                self.sim_thread.stop()
                self._cancel_btn.setEnabled(False)
                self._run_simulation_btn.setEnabled(True)
                self._run_simulation_btn.setText("run")
            else:  # Keep Running or closed dialog
                return

    def _update_progress_text(self, msg):
        self._text_output.appendPlainText(msg)

    def _on_simulations_finished(self, results):
        logging.info("Simulations done, saving.")
        self.simulation_done.emit("Simulations are done!")
        from IPython import embed   
        embed()
        self._text_output.insertPlainText("\nSimulations finished")
        self._results = results
        if self._save_flag:
            filename = Path(self._input_path_edit.text()).stem
            outpath = Path(self._output_path_edit.text())
            if self._save_features_checkbox.isChecked():
                save_features_table(self._results, outpath , filename)
                self._text_output.insertPlainText('\nFeatures were saved\n')
        self._run_simulation_btn.setEnabled(True)
        self._run_simulation_btn.setText("run")
        self._cancel_btn.setEnabled(False)
