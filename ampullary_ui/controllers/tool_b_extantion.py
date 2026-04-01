import multiprocessing
import numpy as np
import pandas as pd
from pathlib import Path
from PySide6.QtCore import QThread, Signal, QUrl, Qt
from PySide6.QtGui import QDesktopServices
from ampullary_ui.computations.table_conversion_gui import prepare_feature_inputs, load_posterior, worker_function_generate_multi
from ampullary_ui.utils import get_outputfolder, save_parameter_table
from ampullary_ui.dialogs.cancelconformdialog import CancelConfirmDialog

from IPython import embed



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



class ToolBExtention:
    #def __init__(self, window, example_fig, feature_labels):

    def __init__(self, main_controller):
        # attributes
        self.main_controller = main_controller
        self.window = self.main_controller._window
        self.results = None
        self.save_flag = True
        self.sim_thread = None  # Initialize thread variable
        self.find_widgets()
        self.setup_defaults()
        self.connect_signals()


    # initialization and setup
    def find_widgets(self):
        self.btn_run = self.window.tc_btn_run
        self.btn_cancel = self.window.tc_btn_cancel
        self.input_path_widget = self.window.tc_input_path
        self.output_path_widget = self.window.tc_output_path
        self.text_output = self.window.tc_text_output
        self.btn_back = self.window.tc_back_to_main
        self.btn_single = self.window.tc_to_single
        self.info_text = self.window.tc_info


    def setup_defaults(self):
        # set other defaults
        self.btn_cancel.setEnabled(False)
        self.input_path_widget.setText("examples/example_features.csv")
        self.output_path_widget.setText("None")
        self.info_text.setOpenExternalLinks(False)
        self.info_text.setOpenLinks(False)

    def open_example(self, url: QUrl):
        rel_path = Path(url.toString())
        base_dir = Path(__file__).resolve().parent
        abs_path = (base_dir / rel_path).resolve()
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(abs_path)))

    def connect_signals(self):
        # connect button clicks to methode
        self.btn_run.clicked.connect(self.on_generate_multi)
        self.btn_cancel.clicked.connect(self.on_cancelled)
        self.info_text.anchorClicked.connect(self.open_example)

    # user input
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
        

    # user actions (button pressed)
    def on_generate_multi(self):
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
        params = pd.read_csv(self.input_path)
        self.text_output.insertPlainText("\nGenerating models...")
        self.sim_thread = GenerationThreadMulti(params)
        self.sim_thread.progress.connect(self.update_progress_text)
        self.sim_thread.finished.connect(self.on_genmulti_finished)
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

    # async / callback handlers
    def update_progress_text(self, msg):
        self.text_output.appendPlainText(msg)

    def on_genmulti_finished(self, results):
        self.main_controller.stop_progress_animation()
        self.text_output.insertPlainText("\nfinished\n")
        self.results = results
        if self.save_flag: 
            filename = self.input_path.stem  # get base filename without extension
            save_parameter_table(results, self.output_path, filename)
            self.text_output.insertPlainText("saved\n")
        # save results function here
        self.btn_run.setEnabled(True)
        self.btn_run.setText("run")
        self.btn_back.setEnabled(True)
        self.btn_single.setEnabled(True)
        self.btn_cancel.setEnabled(False)


    

