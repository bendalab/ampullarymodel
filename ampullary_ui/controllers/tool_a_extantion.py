import multiprocessing
import numpy as np
import pandas as pd
from pathlib import Path
from PySide6.QtCore import QThread, Signal, QUrl
from PySide6.QtGui import QDesktopServices
from ampullary_ui.computations.table_conversion_gui import worker_function_simulate_multi,  package_parameters
from ampullary_ui.utils import get_stimulus_and_data, save_features_table  #, save_data_table
from ampullary_ui.controllers.cancelconformdialog import CancelConfirmDialog

from IPython import embed


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
    def __init__(self, main_controller, parent=None):
        self.__init__(parent)
        self.main_controller = main_controller
        self.window = self.main_controller._window
        self.results = None
        self.save_flag = True
        self.sim_thread = None
        self.find_widgets()
        self.setup_defaults()
        self.connect_signals()

    # initialization and setup
    def find_widgets(self):
        self.btn_run = self.window.ts_btn_run
        self.btn_cancel = self.window.ts_btn_cancel
        self.input_path_widget = self.window.ts_input_path
        self.output_path_widget = self.window.ts_output_path
        self.checkBox_data = self.window.ts_checkBox_data
        self.checkBox_features = self.window.ts_checkBox_features
        self.btn_back = self.window.ts_back_to_main
        self.btn_single = self.window.ts_to_single
        self.text_output = self.window.ts_text_output
        self.info_text = self.window.ts_info

    def setup_defaults(self):
        # set other defaults
        self.btn_cancel.setEnabled(False)
        self.checkBox_data.setChecked(True)
        self.checkBox_features.setChecked(True)
        self.input_path_widget.setText("examples/example_parameters.csv")
        self.output_path_widget.setText("None")
        self.info_text.setOpenExternalLinks(False)
        self.info_text.setOpenLinks(False)

    def open_example(self, url: QUrl):
        rel_path = Path(url.toString())
        base_dir = Path(__file__).resolve().parent
        abs_path = (base_dir / rel_path).resolve()
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(abs_path)))

    def connect_signals(self):
        self.btn_run.clicked.connect(self.on_simulate)
        self.btn_cancel.clicked.connect(self.on_cancelled)
        self.info_text.anchorClicked.connect(self.open_example)
        # connect checkboxes state changes
        self.checkBox_data.stateChanged.connect(self.on_checkbox_changed)
        self.checkBox_features.stateChanged.connect(self.on_checkbox_changed)

    def path_handling(self):
        # Base directory, project root folder:
        # yes, this is bad form with the hardcoded folder depth, I do not care right now
        # change if folder structure changes or for better maintainability
        base_dir = Path(__file__).resolve().parents[2]
        input_path_str = self.input_path_widget.text().strip()
        input_path = (base_dir / input_path_str).resolve()
        output_path_str = self.output_path_widget.text().strip()
        if output_path_str and output_path_str.lower() != "none":
            # path exists and is not None in any form
            output_path = (base_dir / output_path_str).resolve()
        else:
            # No output path given, use input's parent directory as output folder
            output_path = input_path.parent
        return input_path, output_path

    def path_validating(self, input_path, output_path):
        if not input_path.exists():
            self.text_output.appendPlainText(f"Input file does not exist: {input_path}")
            return False  # stop further processing
        if not input_path.is_file():
            self.text_output.appendPlainText(f"Input path is not a file: {input_path}")
            return False  # stop further processing
        self.text_output.appendPlainText(f"Input file found: {input_path}")
        self.text_output.appendPlainText(f"Output path set to: {output_path}")
        return True

    def on_simulate(self):
        if hasattr(self, 'sim_thread') and self.sim_thread.isRunning():
            self.text_output.appendPlainText("Please wait for current subprocess to be cancelled.")
            return

        self.btn_run.setEnabled(False)
        self.btn_run.setText("running…")
        self.main_controller.start_progress_animation()
        self.btn_back.setEnabled(False)
        self.btn_single.setEnabled(False)
        self.btn_cancel.setEnabled(True)

        self.input_path, self.output_path = self.path_handling()

        if not self.path_validating(self.input_path, self.output_path):
            # Abort simulation: reset back so user can try again
            self.btn_run.setEnabled(True)
            self.btn_run.setText("run")
            self.main_controller.stop_progress_animation()
            self.btn_back.setEnabled(True)
            self.btn_single.setEnabled(True)
            self.btn_cancel.setEnabled(False) 
            return  # just do nothing else

        # If validation passed, continue:
        parameters = pd.read_csv(self.input_path)
        params = package_parameters(parameters)
        save_raw = self.checkBox_data.isChecked()
        calc_feats = self.checkBox_features.isChecked()
        self.text_output.insertPlainText("\nSimulating in chunks of 100...\n")
        self.sim_thread = SimulationThreadMulti(params, save_raw, calc_feats, self.input_path, self.output_path)
        self.sim_thread.progress.connect(self.update_progress_text)
        self.sim_thread.finished.connect(self.on_simmulti_finished)
        self.sim_thread.finished.connect(self.sim_thread.quit)  # Clean up thread when done
        self.sim_thread.finished.connect(self.sim_thread.deleteLater)
        self.sim_thread.start()

    def on_cancelled(self):
        if hasattr(self, 'sim_thread') and self.sim_thread.isRunning():
            dlg = CancelConfirmDialog(self.btn_cancel)
            result = dlg.exec()

            if result == 1:  # Save and Cancel
                self.sim_thread.stop()
                self.btn_cancel.setEnabled(False)
                self.btn_run.setEnabled(True)
                self.btn_run.setText("run")
                # saving handled in on_simulation_finished
            elif result == 2:  # Cancel without saving
                self.save_flag = False
                self.sim_thread.stop()
                self.btn_cancel.setEnabled(False)
                self.btn_run.setEnabled(True)
                self.btn_run.setText("run")
            else:  # Keep Running or closed dialog
                return

    def on_checkbox_changed(self):
        if not (self.checkBox_data.isChecked() or self.checkBox_features.isChecked()):
            self.btn_run.setEnabled(False)
            self.text_output.appendPlainText("Select at least one option to run simulation")
        else:
            self.btn_run.setEnabled(True)

    # async / callback handlers
    def update_progress_text(self, msg):
        self.text_output.appendPlainText(msg)

    # async / callback handlers
    def on_simmulti_finished(self, results):
        self.main_controller.stop_progress_animation()
        self.text_output.insertPlainText("\nSimulations finished")
        self.results = results
        if self.save_flag: 
            filename = self.input_path.stem  # get base filename without extension
            if self.checkBox_features.isChecked():
                save_features_table(self.results, self.output_path , filename)
                self.text_output.insertPlainText('\nFeatures were saved\n')
        self.btn_run.setEnabled(True)
        self.btn_run.setText("run")
        self.btn_back.setEnabled(True)
        self.btn_single.setEnabled(True)
        self.btn_cancel.setEnabled(False)
