import os
import numpy as np
from PySide6.QtWidgets import QDoubleSpinBox, QSizePolicy, QFrame
from PySide6.QtCore import QThread, Signal, QLocale
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from ampullary_ui.computations.controller_functions import simulate_from_input_params, create_cell_from_input_features
from ampullary_ui.computations.saving_helper import save_params, save_data, save_features
from ampullary_ui.plotting.plot_cell import plot_cell
from IPython import embed




class SimulationThread(QThread):
    finished = Signal(object)  # emits results when done
    def __init__(self, params):
        super().__init__()
        self.params = params

    def run(self):
        # This runs in a separate thread!
        results = simulate_from_input_params(self.params)
        self.finished.emit(results)



class GenerationThread(QThread):
    finished = Signal(object)  # emits results when done
    def __init__(self, features):
        super().__init__()
        self.features = features

    def run(self):
        # This runs in a separate thread!
        results = create_cell_from_input_features(self.features)
        self.finished.emit(results)






class ToolBController:
    """
    Generate model from feature set
    Simulate with this model to estimate model fit
    """
    #def __init__(self, window, example_fig, parameter_labels, feature_labels, main_controller):
    def __init__(self, main_controller, parameter_labels, feature_labels):
        # attributes
        self.main_controller = main_controller
        #self.window = window
        #self.current_fig = example_fig
        self.window = self.main_controller.window # see if scip and just use while in find widgets
        self.example_fig = self.main_controller.example_fig
        self.current_fig = self.example_fig
        self.params = None
        self.results = None
        self.canvas = None
        self.parameter_labels = parameter_labels
        self.feature_labels = feature_labels
        self.sim_thread = None  # Initialize thread variable
        self.find_widgets()
        self.setup_spinboxes()
        self.setup_defaults()
        self.setup_placeholder_plot()
        self.connect_signals()


    # initialization and setup
    def find_widgets(self):
        self.btn_generate = self.window.cm_btn_generate
        self.btn_simulate = self.window.cm_btn_simulate
        self.btn_save_params = self.window.cm_btn_save_params
        self.btn_save = self.window.cm_btn_save
        self.btn_reset = self.window.cm_btn_reset
        self.text_output = self.window.cm_text_output
        self.name_edit = self.window.cm_input_name
        self.checkBox_data = self.window.cm_checkBox_data
        self.checkBox_features = self.window.cm_checkBox_features
        self.btn_back = self.window.cm_back_to_main
        self.btn_multi = self.window.cm_table_version
        # I don’t strictly need to store them, but it makes code easier to read, i know where to look if something breaks
        # and if i rename widgets, I only neet to change it here! 
        self.plot_container = self.window.findChild(QFrame, "cm_figure")
        self.spinboxes = [
            self.window.findChild(QDoubleSpinBox, f"cm_doubleSpinBox_{i}")
            for i in range(1, 18)]


    def setup_spinboxes(self):
        # set spinbox defaults
        self.spinbox_settings = [
            {"min": 30.0, "max": 250.0, "default": 123.27},
            {"min": 0.0,  "max": 4.67, "default": 0.04},
            {"min": -0.94,  "max": 0.99, "default": -0.18},
            {"min": 0.0,  "max": 600.0, "default": 20.82},
            {"min": 0.02, "max": 1.0, "default": 0.78},
            {"min": 0.06, "max": 1.0, "default":  0.93},
            {"min": 0.03, "max": 0.98, "default":  0.04},
            {"min": 0.0, "max": 148.93, "default":  12.21},
            {"min": 03.66, "max": 148.93, "default":  47.61},
            {"min": 0.0, "max": 26177.93, "default":  62.66},
            {"min": 0.0,  "max": 38850.74, "default":  137.97},
            {"min": 0.0,  "max": 45872.02, "default":  166.75},
            {"min": 0.0,  "max": 1336.96, "default":  62.56},
            {"min": 0.0,  "max": 2146.2, "default":  36.63},
            {"min": 0.0, "max": 74.46, "default": 10.99},
            {"min": 0.0, "max": 148.93, "default":  21.97},
            {"min": 0.0, "max": 148.93, "default":  48.83}]
        steps = np.zeros(len(self.spinbox_settings))
        for k in [1,2] + list(range(4, 7)):
            steps[k] = 0.01
        for k in [0, 3] + list(range(7, 16)):
            steps[k] = 1.0
        for i, settings in enumerate(self.spinbox_settings, start=0):
            sb = self.spinboxes[i]
            if sb is not None:
                sb.setMinimum(settings["min"])
                sb.setMaximum(settings["max"])
                sb.setValue(settings["default"])
                sb.setDecimals(2)
                sb.setSingleStep(steps[i])
                # Use a point as decimal separator
                sb.setLocale(QLocale(QLocale.C))  


    def setup_defaults(self):
        # set other defaults
        self.btn_save_params.setEnabled(False)
        self.btn_reset.setEnabled(False)
        self.btn_simulate.setEnabled(False)
        self.btn_save.setEnabled(False)
        self.name_edit.setText("model_001")
        self.checkBox_data.setChecked(True)
        self.checkBox_features.setChecked(False)


    def setup_placeholder_plot(self):
        self.plot_layout = self.plot_container.layout()
        # Create a matplotlib canvas for the example figure placeholder
        self.placeholder_canvas = FigureCanvas(self.current_fig)  # current_fig now holds example_fig
        self.placeholder_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.plot_layout.addWidget(self.placeholder_canvas)
        

    def connect_signals(self):
        # connect button clicks to methode
        self.btn_generate.clicked.connect(self.on_generate)
        self.btn_reset.clicked.connect(self.on_reset)
        self.btn_simulate.clicked.connect(self.on_simulate)
        self.btn_save_params.clicked.connect(self.on_save_params)
        self.btn_save.clicked.connect(self.on_save)


    # user actions (button pressed)
    def on_generate(self):
        self.btn_generate.setEnabled(False)
        self.btn_generate.setText("generating…")
        self.main_controller.start_progress_animation()
        self.btn_back.setEnabled(False)
        self.btn_multi.setEnabled(False)
        self.features = [self.spinboxes[i].value() for i in range(0, 17)]
        self.text_output.clear()
        self.text_output.insertPlainText("Computing MAP model from posterior...\n")
        self.sim_thread = GenerationThread(self.features)
        self.sim_thread.finished.connect(self.on_generation_finished)
        self.sim_thread.finished.connect(self.sim_thread.quit)  # Clean up thread when done
        self.sim_thread.finished.connect(self.sim_thread.deleteLater)
        self.sim_thread.start()


    def on_simulate(self):
        self.btn_simulate.setEnabled(False)
        self.btn_simulate.setText("simulating…")
        self.main_controller.start_progress_animation()
        self.btn_back.setEnabled(False)
        self.btn_multi.setEnabled(False)
        self.btn_reset.setEnabled(False)
        self.btn_generate.setEnabled(False)
        self.btn_save_params.setEnabled(False)
        self.text_output.insertPlainText("\nSimulating...")
        self.sim_thread = SimulationThread(self.params)
        self.sim_thread.finished.connect(self.on_simulation_finished)
        self.sim_thread.finished.connect(self.sim_thread.quit)  # Clean up thread when done
        self.sim_thread.finished.connect(self.sim_thread.deleteLater)
        self.sim_thread.start()

    
    def on_reset(self):
        self.btn_reset.setEnabled(False)
        self.btn_simulate.setEnabled(False)
        self.btn_save_params.setEnabled(False)
        self.btn_save.setEnabled(False)
        self.name_edit.setText("model_001")
        self.checkBox_data.setChecked(True)
        self.checkBox_features.setChecked(False)
        for i, settings in enumerate(self.spinbox_settings):
            sb = self.spinboxes[i]
            sb.setValue(settings["default"])
        self.current_fig = self.example_fig
        self.show_simulation_figure()
        self.text_output.clear()
        self.text_output.insertPlainText('Describe the cell you want to model by the offered features. A best-guess model that will generate your feature set will be proposed. You can immediately check how well the model fits be using it to simulate data and compare the simulated features with your input.') 



    # async / callback handlers
    def on_generation_finished(self, params):
        self.main_controller.stop_progress_animation()
        self.params = params
        # Enable the save params button now that results are available
        self.btn_save_params.setEnabled(True)
        self.btn_reset.setEnabled(True)
        self.btn_simulate.setEnabled(True)
        self.btn_generate.setEnabled(True)
        self.btn_generate.setText("generate")
        self.btn_back.setEnabled(True)
        self.btn_multi.setEnabled(True)
        # print features
        self.print_params()


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
        self.btn_generate.setEnabled(True)
        self.btn_reset.setEnabled(True)
        self.btn_save_params.setEnabled(True)
        self.btn_back.setEnabled(True)
        self.btn_multi.setEnabled(True)
        self.text_output.insertPlainText(' simulation finished\n')
        # print features
        self.print_feature_comparison()

    
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
    def print_params(self):
        # print the features into the window
        self.text_output.clear() # get rid of the Generating... 
        self.text_output.insertPlainText('Your model has the following parameters:\n\n')
        label_width = max(len(s) for s in self.parameter_labels)
        for i, label in enumerate(self.parameter_labels):
            line = f'{label + ":":<{label_width + 1}} {np.round(self.params[i], 2)}\n'
            self.text_output.insertPlainText(line)


    def print_feature_comparison(self):
        # print the features into the window
        self.text_output.insertPlainText('\nYour simulated cell has the following features:\n')
        label_width = max(len(s) for s in self.feature_labels)
        f_s =  ["%.2f" % number for number in self.features]
        f_width = max(len(f) for f in f_s)
        for i, label in enumerate(self.feature_labels):
            line = f'{label + ":":<{label_width + 1}} --> wanted: {np.round(self.features[i], 2):<{f_width + 1}} --> got: {np.round(self.results.features[i], 2)}\n'
            self.text_output.insertPlainText(line)


    # saving   
    def on_save_params(self):
        filename = self.name_edit.text().strip()
        if self.params is None:
            self.text_output.insertPlainText('\nNothing to save\n')
            return
        else:
            save_params(self.params, filename)
            self.text_output.insertPlainText('\nParameter were saved\n')


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



    


