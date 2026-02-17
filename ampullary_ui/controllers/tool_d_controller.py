import os 
import pandas as pd
import numpy as np
from PySide6.QtWidgets import QLineEdit, QSpinBox, QFrame, QSizePolicy
from PySide6.QtCore import Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from ampullary_ui.computations.controller_functions import get_subset_values
from ampullary_ui.plotting.plot_distro import plot_samples
from ampullary_ui.computations.saving_helper import save_sampled_subset
from IPython import embed




class ToolDController:
    def __init__(self, window, data, prior_samples, labels):
        self.window = window 
        self.canvas = None
        self.current_fig = None
        self.find_widgets()
        self.setup_defaults()
        self.data = data
        self.titles = labels
        self.prior_samples = prior_samples
        self.setup_placeholder_plot()
        self.connect_signals()
        


    # initialization and setup
    def find_widgets(self):
        self.btn_search = self.window.gme_btn_search
        self.btn_save = self.window.gme_btn_save
        self.name_edit = self.window.gme_name_input
        self.btn_back = self.window.gme_back_to_main
        self.btn_switch = self.window.gme_switch_to_c
        self.sample_n = self.window.findChild(QSpinBox, f"gme_spinBox_1")
        self.plot_container = self.window.findChild(QFrame, "gme_figure")
        self.inputs = [self.window.findChild(QLineEdit, f"gme_lineEdit_{i}") for i in range(1, 18)]


    def setup_defaults(self):
        # note: dont need to set up range, if its to high/low, i will just take the nearest (highest/lowest) anyway
        self.btn_save.setEnabled(False)
        self.name_edit.setText("subset_001")
        self.sample_n.setMinimum(1)
        self.sample_n.setMaximum(12_000_000) #!!!
        self.sample_n.setValue(100)
        self.inputs = [self.window.findChild(QLineEdit, f"gme_lineEdit_{i}") for i in range(1, 18)]
        for line in self.inputs:
            line.setPlaceholderText("None")
            line.setAlignment(Qt.AlignRight)
            #line.setFixedWidth(80)
            line.setStyleSheet("""QLineEdit:placeholder{color: #888;}""")
    

    def setup_placeholder_plot(self):
        #make dummy fig with all samples:
        values = np.array([100, 0.12]+[np.nan]*15)
        n = 100
        self.near_data_samples, self.near_prior_samples = get_subset_values(self.data, self.prior_samples, values, n)
        fig = plot_samples(values, self.near_data_samples, self.titles)
        self.current_fig = fig
        fig.text(0.5, 0.5, "EXAMPLE", fontsize=80, fontweight='bold', color='#44F9BD', alpha=0.6, ha='center', va='center', rotation=40, zorder=10)
        # Display the figure
        self.plot_layout = self.plot_container.layout()
        # Create a matplotlib canvas for the example figure placeholder
        self.placeholder_canvas = FigureCanvas(fig)  # current_fig now holds example_fig
        self.placeholder_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.plot_layout.addWidget(self.placeholder_canvas)


    def connect_signals(self):
        self.btn_search.clicked.connect(self.on_search)
        self.btn_save.clicked.connect(self.on_save)


    # user actions (button pressed)
    def on_search(self):
        # disabeling here might be overkill since its so fast, but maybe for other users, ask jan
        self.btn_search.setEnabled(False)
        self.btn_search.setText("Searching…")
        self.btn_back.setEnabled(False)
        self.btn_switch.setEnabled(False)
        values = self.get_values_from_lines()
        n = int(self.sample_n.value())
        self.near_data_samples, self.near_prior_samples = get_subset_values(self.data, self.prior_samples, values, n)
        # figure
        fig = plot_samples(values, self.near_data_samples, self.titles)
        self.current_fig = fig
        # Display the figure
        self.show_simulation_figure()
        # enable again
        self.btn_search.setEnabled(True)
        self.btn_search.setText("Search samples")
        self.btn_save.setEnabled(True)
        self.btn_back.setEnabled(True)
        self.btn_switch.setEnabled(True)


    def on_save(self):
        filename = self.name_edit.text().strip()
        save_sampled_subset(self.near_data_samples, self.near_prior_samples, filename)
        # disable save button after saving once 
        # --> actually makes sense here
        self.btn_save.setEnabled(False)


    # some computation helper
    def get_values_from_lines(self):
        vals_convert = np.full(len(self.inputs), np.nan, dtype=float)  # Initialize with NaNs
        for i, line in enumerate(self.inputs):
            text = line.text().strip()
            if text == "" or text.lower() == "none":
                # Keep NaN for empty or "None"
                continue
            try:
                # Replace commas with dots if any, to handle user mistakes
                normalized_text = text.replace(',', '.')
                val = float(normalized_text)
                vals_convert[i] = val
            except ValueError:
                # Invalid input → np.nan
                vals_convert[i] = np.nan
        return vals_convert


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








    



"""
    def save_sampled_subset(self):
        output_dir = os.path.join( "..", "derived_data", "subsets") 
        os.makedirs(output_dir, exist_ok=True)
        filename = self.name_edit.text().strip()
        df_sum_subset_samples = pd.DataFrame(data =  self.near_data_samples, columns = self.labels["feature_save_labels"])
        filepath = os.path.join(output_dir, f"feature_sample_subset_{filename}.csv")
        df_sum_subset_samples.to_csv(filepath, index = False) 
        df_prior_subset_samples = pd.DataFrame(data = self.near_prior_samples,columns = self.labels["parameter_save_labels"])
        filepath = os.path.join(output_dir, f"prior_sample_subset_{filename}.csv")
        df_prior_subset_samples.to_csv(filepath, index = False) 
        # disable save button
        self.btn_save.setEnabled(False)
"""

#pip uninstall sbi && pip install sbi==0.22.0 