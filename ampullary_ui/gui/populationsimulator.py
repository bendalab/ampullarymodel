import logging
import numpy as np
import pandas as pd
import multiprocessing

from pathlib import Path

from PySide6.QtWidgets import QWidget, QFileDialog
from PySide6.QtCore import Signal, QThread

from ampullary_ui.ui.populationsimulator_ui import Ui_PopulationSimulator
from ampullary_ui.simulation.table_conversion_gui import package_parameters
from ampullary_ui.dialogs import CancelConfirmDialog
from ampullary_ui.utils import read_output_folder, save_features_table, load_gwnstimulus, modify_stimulus
from ampullary_ui.analysis import summary_statistics
from ampullary_ui.simulation.lif_simulation import package_parameters, ampullary_lif
from ampullary_ui.analysis.utils import split_data, spiketimes_to_trials


def worker_function(start_idx, package_params, stimulus,
                    stim_data, result_queue, progress_queue,
                    save_raw, calc_feats, save_dir):
    """
    Worker function for running a single LIF simulation in a multiprocessing setup.

    This function wraps the full simulation pipeline for one parameter package (max 100 sets):
    it generates a timed stimulus, runs the LIF simulation, optionally saves minimally pre-processed simulation data, optionally computes features,
    and communicates results back through multiprocessing queues.

    Parameters
    ----------
    start_idx : int
        Index identifying the current simulation job for naming saved files.
    packages_params : list of list of arrays
        list of packages of max 100 model parameter sets for `lif_simulation`
    stimulus : np.array
        stimulus size corresponding to each time point, dt = default 50us
        Input stimulus array to be converted into a `TimedArray` and passed to the simulation.
    stim_data : dict
        GWN Stimulus used for training, dictionary includes stimulus itself, as well as meta data and time array
    result_queue : multiprocessing.Queue
        Queue used to return results to the parent process. On success,
        a dictionary with keys:
            - "features": computed summary statistics or None
            - "saved_flag": bool indicating whether raw data was saved
        On failure, `None` is placed in the queue.
    progress_queue : multiprocessing.Queue
        Queue used to report progress or error messages to the parent process.
    save_raw : bool
        If True, raw simulation output is wrapped and saved to disk.
    calc_feats : bool
        If True, summary statistics are computed from the simulation output.
    save_dir : str
        Directory path where simulation data will be stored if`save_raw` is True.

    Returns
    -------
    None
        Results are returned via `result_queue`. Errors are reported via `progress_queue`.
    """

    saved_flag = False
    features = None
    try:
        print(package_params)
        print(stimulus)
        sim_data = ampullary_lif(package_params, stimulus, record_voltage=False)
        print(sim_data)
        if save_raw:
            print(save_raw)
            saved_flag = save_data(sim_data, stim_data, save_dir, package_params, start_idx)
        if calc_feats:
            features = summary_statistics(sim_data, stim_data)
        del sim_data
        result_queue.put({"features": features, "saved_flag": saved_flag})
    except Exception as e:
        progress_queue.put(f'Error: {str(e)}')
        print(e)
        result_queue.put(None)


def save_data(lif_data, stim_data, save_dir, params, start_idx,
              baseline_duration=30.):
    """
    Convert raw simulation data into pre-processed data format and save data

    Separate simulated data of baseline activity from simulated data during stimulation with gwn
    Compute spike times relative to stimulus start for all repetitions of the stimulation
    Pack together and save as .npz
    
    sim_data: dictionary 
        dictionary with spike_idx, spike_times and time array
    stim_data : dict
        GWN Stimulus used for training, dictionary includes stimulus itself, as well as meta data and time array
    save_dir: str
        Directory path where simulation data will be stored
    params : np.array
        array of arrays with model parameter sets
    start_idx : int
        Index identifying the current simulation job for naming saved files.

    Returns
    -------
    True : bool
        check for "ran"
    """
    stimulus_duration = stim_data["duration"]
    baseline, stimulation = split_data(lif_data, baseline_duration, stimulus_duration)

    trials = spiketimes_to_trials(stimulation)
    for i in range(len(trials['spikes'])):
        cell_id = start_idx + i
        filepath = save_dir / f"cell_{cell_id}.npz"
        print(filepath)
        np.savez_compressed(filepath, baseline_time=np.round(baseline['time'], 7),
                            baseline_spikes=baseline['spikes'][i],
                            whitenoise_time = np.round(trials['time'], 7),
                            whitenoise_spikes = np.array(trials['spikes'][i], dtype=object),
                            params = params[i])
    return True


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
            self.current_proc = multiprocessing.Process(target=worker_function, 
                                                        args=(start_idx, package_params, stimulus, stim_data,
                                                              self.result_queue, self.progress_queue, 
                                                              self.save_raw, self.calc_feats, raw_data_dir))
            self.current_proc.start()
            self.current_proc.join()

            # Try to get result if any
            try:
                result = self.result_queue.get_nowait()
                if result is None:
                    print("results are None!")
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
        print(self.sim_thread)
        logging.info("Simulations done, saving.")
        self.simulation_done.emit("Simulations are done!")
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
