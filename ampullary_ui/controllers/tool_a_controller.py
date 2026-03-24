import numpy as np
import logging

from PySide6.QtWidgets import QDoubleSpinBox, QSizePolicy, QFrame
from PySide6.QtCore import QThread, Signal, QLocale
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from ampullary_ui.computations.controller_functions import simulate_from_input_params
from ampullary_ui.computations.saving_helper import save_data, save_features, save_figure
from ampullary_ui.plotting.plot_cell import plot_cell
from IPython import embed

logging.info(f"ToolA controller: imports done")
class SimulationThread(QThread):
    finished = Signal(object)  # emits results when done

    def __init__(self, params):
        super().__init__()
        self.params = params

    def run(self):
        # This runs in a separate thread!
        results = simulate_from_input_params(self.params)
        self.finished.emit(results)


class ToolAController:
    #def __init__(self, window, example_fig, feature_labels):

    def __init__(self, main_controller, feature_labels):
        # attributes
        self.main_controller = main_controller
        #self.window = window
        #self.current_fig = example_fig
        self.window = self.main_controller.window
        self.example_fig = self.main_controller.example_fig
        self.current_fig = self.example_fig
        self.results = None
        self.canvas = None
        self.labels = feature_labels
        self.sim_thread = None
        self.find_widgets()
        self.setup_spinboxes()
        self.setup_defaults()
        self.setup_placeholder_plot()
        self.connect_signals()


    # initialization and setup
    def find_widgets(self):
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


    def setup_spinboxes(self):
        # set spinbox defaults
        self.spinbox_settings = [
            {"min": 0.01, "max": 40.0, "default": 21.46},
            {"min": 0.0,  "max": 3.0, "default": 2.47},
            {"min": 1.0,  "max": 100.0, "default": 33.25},
            {"min": 0.0,  "max": 3.0, "default": 3.14},
            {"min": -100.0,  "max": 0.0, "default": -15.62},
            {"min": 0.01, "max": 15.0, "default":7.32},
            {"min": 0.01, "max": 500.0, "default": 43.44},
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


    def setup_defaults(self):
        # set other defaults
        self.btn_simulate.setEnabled(True)
        self.btn_save.setEnabled(False)
        self.btn_reset.setEnabled(False)
        self.name_edit.setText("simulation_001")
        self.checkBox_data.setChecked(True)
        self.checkBox_features.setChecked(False)
        self.checkBox_figure.setChecked(False)


    def setup_placeholder_plot(self):
        self.plot_layout = self.plot_container.layout()
        # Create a matplotlib canvas for the example figure placeholder
        self.placeholder_canvas = FigureCanvas(self.current_fig)  # current_fig now holds example_fig
        self.placeholder_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.plot_layout.addWidget(self.placeholder_canvas)


    def connect_signals(self):
        # connect button clicks to methode
        self.btn_simulate.clicked.connect(self.on_simulate)
        self.btn_reset.clicked.connect(self.on_reset)
        self.btn_save.clicked.connect(self.on_save)


    # user actions (button pressed)
    def on_simulate(self):
        self.btn_simulate.setEnabled(False)
        self.btn_reset.setEnabled(False)
        self.btn_simulate.setText("simulating…")
        self.main_controller.start_progress_animation()
        self.btn_save.setEnabled(False)
        self.btn_back.setEnabled(False)
        self.btn_multi.setEnabled(False)
        params = [self.spinboxes[i].value() for i in range(0, 9)]
        self.text_output.clear()  # clear previous messages, if I want to insert a startring message
        # could print the explanation test in window and get rid of it as extra widget?
        self.text_output.insertPlainText("Simulating...\n")
        self.sim_thread = SimulationThread(params)
        self.sim_thread.finished.connect(self.on_simulation_finished)
        self.sim_thread.finished.connect(self.sim_thread.quit)  # Clean up thread when done
        self.sim_thread.finished.connect(self.sim_thread.deleteLater)
        self.sim_thread.start()

    def on_reset(self):
        self.btn_reset.setEnabled(False)
        self.btn_save.setEnabled(False)
        self.name_edit.setText("simulation_001")
        for i, settings in enumerate(self.spinbox_settings):
            sb = self.spinboxes[i]
            sb.setValue(settings["default"])
        self.current_fig = self.example_fig
        self.show_simulation_figure()
        self.text_output.clear()
        self.text_output.insertPlainText('Just put in a set of parameters and press simulate!\n\nThe simualtion includes 30 ms baseline activity and 100s white noise, which you can find in the stimuli folder.') 




    # async / callback handlers
    def on_simulation_finished(self, results):
        self.main_controller.stop_progress_animation()
        self.results = results
        # Create the matplotlib figure from your data
        fig = plot_cell(self.results.baseplot, self.results.stimplot)
        self.current_fig = fig
        # Display the figure
        self.show_simulation_figure()
        # Enable the save button now that results are available
        self.btn_save.setEnabled(True)
        self.btn_simulate.setEnabled(True)
        self.btn_simulate.setText("simulate")
        self.btn_back.setEnabled(True)
        self.btn_multi.setEnabled(True)
        self.btn_reset.setEnabled(True)
        self.text_output.clear()
        # print features
        self.print_features()


    # update figure   
    def show_simulation_figure(self):
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


    def redraw_figure(self):
        if self.canvas:
            self.canvas.draw_idle()
            self.canvas.resize(self.canvas.size())


    # print results
    def print_features(self):
        # print the features into the window
        self.text_output.insertPlainText('Your simulated cell has the following features:\n\n')
        label_width = max(len(s) for s in self.labels)
        for i, label in enumerate(self.labels):
            line = f'{label + ":":<{label_width + 1}} {np.round(self.results.features[i], 2)}\n'
            self.text_output.insertPlainText(line)


    # saving   
    def on_save(self):
        # save everything that is checked when savebutton is clicked
        filename = self.name_edit.text().strip()
        if self.results is None:
            self.text_output.insertPlainText('\nNothing to save\n')
            return
        if self.checkBox_data.isChecked():
            save_data(self.results.data, filename)
            self.text_output.insertPlainText('\nData was saved\n')
        if self.checkBox_features.isChecked():
            save_features(self.results.features, filename) 
            self.text_output.insertPlainText('\nFeatures were saved\n')
        if self.checkBox_figure.isChecked():
            if hasattr(self, 'current_fig'):
                save_figure(self.current_fig, filename)
                self.text_output.insertPlainText('\nFigure was saved\n')
            else:
                self.text_output.insertPlainText('\nNo figure to save\n')


