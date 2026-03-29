import logging
import random
import numpy as np

from pathlib import Path

from PySide6.QtWidgets import QSpinBox, QWidget, QFileDialog
from PySide6.QtCore import Signal, QThread, QTimer, QSettings
from ampullary_ui.controllers.customcombienationwidget import RangeCombine
from ampullary_ui.utils.saving_helper import save_sampled_subset, get_outputfolder
from IPython import embed


class FullHistogramWorker(QThread):
    finished = Signal(list)

    def __init__(self, data, mins, maxs, bin_specs):
        super().__init__()
        self.data = data
        self.mins = mins
        self.maxs = maxs
        self.bin_specs = bin_specs
    
    def make_shared_mask(self):
        mask = np.ones(len(self.data), dtype=bool)
        for i in range(len(self.data[0])):
            mask &= (self.data[:,i] >= self.mins[i]) & (self.data[:, i] <= self.maxs[i])
        return mask


    def compute_bins(self, col_data, min_value, max_value, bin_spec):
        if isinstance(bin_spec, int):
            return np.linspace(min_value, max_value, bin_spec)
        if bin_spec == "numerical":
            values = np.unique(col_data)
            values = values[(values >= min_value) & (values <= max_value)]
            return np.append(values, values[-1] + 1e-9)
        raise ValueError(bin_spec)

    def run(self):
        mask = self.make_shared_mask()
        results = []
        for col in range(self.data.shape[1]):
            col_data = self.data[:, col]
            min_v = self.mins[col]
            max_v = self.maxs[col]
            bin_spec = self.bin_specs[col]
            cropped_data = col_data[mask]
            bins = self.compute_bins(col_data, min_v, max_v, bin_spec)
            full_counts, _ = np.histogram(cropped_data, bins=bins)
            results.append({
                "bins": bins,
                "full": full_counts
            })
        self.finished.emit(results)


class ReducedHistogramWorker(QThread):
    finished = Signal(list)
    def __init__(self, data, mask, hist_cache):
        super().__init__()
        self.data = data
        self.mask = mask
        self.hist_cache = hist_cache

    def run(self):
        results = []
        for col, cached in enumerate(self.hist_cache):
            bins = cached["bins"]
            col_data = self.data[:, col][self.mask]
            reduced_counts, _ = np.histogram(col_data, bins=bins)
            results.append({
                "bins": bins,
                "full": cached["full"],
                "reduced": reduced_counts
            })
        self.finished.emit(results)


class ToolCController:
    """
    Shows distributions and produces interactive plots.
    Make ranges for the features and take samples from within those ranges
    """
    def __init__(self, window, labels):
        self.window = window 
        self.user_compute = False
        self.find_widgets()
        self.setup_defaults()
        self._summarystats = None
        self.titles = labels
        self._priorsamples = None
        self.mins, self.maxs, self.bin_specs, self.decimals, self.steps = self.define_stuff()
        self.full_worker = None  # Initialize worker variables
        self.reduced_worker = None
        self.connect_signals()
        # QTimer.singleShot(0, self.compute_initial_histograms)

    # initialization and setup
    def find_widgets(self):
        self.btn_compute = self.window.gm_btn_compute
        self.btn_save = self.window.gm_btn_save
        self.name_edit = self.window.gm_name_input
        self.btn_back = self.window.gm_back_to_main
        self.btn_switch = self.window.gm_switch_to_d
        self.range_widget_container = self.window.findChild(QWidget, "gm_placeholder")
        self.sample_n = self.window.findChild(QSpinBox, f"gm_spinBox_1")
        self.n_update = self.window.gm_n_update

    def setup_defaults(self):
        self.btn_save.setEnabled(False)
        self.name_edit.setText("subset_001")
        self.sample_n.setMinimum(1)
        self.sample_n.setMaximum(12_000_000)
        self.sample_n.setValue(100)

    def define_stuff(self): 
        mins = [30.0, 0.0, -0.75, 0.0, 0.0, 0.0, 0.0, 0.0, 3.66, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        maxs = [250.0, 1.0, 1.0, 200, 1.0, 1.0, 0.4, 50, 150.0, 1000.0, 2000.0, 3000.0, 400, 100.0, 30.0, 50.0, 100.0]
        bin_specs = {}
        # Assign 200 to keys 0, and 1 to 6, and 9 to 13
        for k in [0] + list(range(1, 7)) + list(range(9, 14)):
            bin_specs[k] = 200
        # Assign 'numerical' to keys 7, 8, 14, 15, 16 (frequency features)
        for k in [7, 8, 14, 15, 16]:
            bin_specs[k] = "numerical"
        decimals = np.zeros(len(mins))
        steps = np.zeros(len(mins))
        for k in [1,2] + list(range(4, 7)):
            steps[k] = 0.01
            decimals[k] = 2
        for k in [0, 3] + list(range(7, 16)):
            steps[k] = 1.0
            decimals[k] = 0
        return mins, maxs, bin_specs, decimals, steps

    def insert_range_widgets(self, cols):
        self.range_widgets = []
        layout = self.range_widget_container.layout()
        if layout is None:
            raise RuntimeError("gm_placeholder_widget has no layout in Qt Designer!")
        for col in range(17):
            rc = RangeCombine(data=self._summarystats[:, col], min_value=self.mins[col], max_value=self.maxs[col], 
                              bin_specs=self.bin_specs[col], decimals=self.decimals[col], step=self.steps[col],
                              label=self.titles[col])
            self.range_widgets.append(rc)
        for i, rc in enumerate(self.range_widgets):
            row_grid = i // cols
            col_grid = i % cols
            layout.addWidget(rc, row_grid, col_grid)

    def set_data(self, summarystats, priorsamples):
        logging.debug("ToolC.set_data: received data")
        self._summarystats = summarystats
        self._priorsamples = priorsamples
        self.insert_range_widgets(3)
        self.compute_initial_histograms()

    def compute_initial_histograms(self):
            if self._summarystats is None:
                return
            self.user_compute = False
            self.btn_compute.setEnabled(False)
            self.btn_compute.setText("loading…")

            self.full_worker = FullHistogramWorker(self._summarystats, self.mins, self.maxs, self.bin_specs)
            self.full_worker.finished.connect(self.on_full_histograms_ready)
            self.full_worker.finished.connect(self.full_worker.quit)  # Clean up thread when done
            self.full_worker.finished.connect(self.full_worker.deleteLater)
            self.full_worker.start()

    def connect_signals(self):
        self.btn_compute.clicked.connect(self.on_compute)
        self.btn_save.clicked.connect(self.on_save)

    # user actions (button pressed)
    def on_compute(self):
        self.user_compute = True
        self.btn_compute.setEnabled(False)
        self.btn_compute.setText("computing…")
        self.btn_back.setEnabled(False)
        self.btn_switch.setEnabled(False)
        self.btn_save.setEnabled(False)
        mask = self.compute_shared_mask()
        self.reduced_worker = ReducedHistogramWorker(self._summarystats, mask, self.hist_cache)
        self.reduced_worker.finished.connect(self.on_histograms_ready)
        self.reduced_worker.finished.connect(self.reduced_worker.quit)  # Clean up thread when done
        self.reduced_worker.finished.connect(self.reduced_worker.deleteLater)
        self.reduced_worker.start()

    def on_save(self):
        output_folder = get_outputfolder()

        data_samples, prior_samples = self.sample_subset_for_saving()
        filename = self.name_edit.text().strip()
        save_sampled_subset(data_samples, prior_samples, output_folder, filename)
        self.btn_save.setText("save another set")

    # core computation parts
    def compute_shared_mask(self):
        mask = np.ones(len(self._summarystats), dtype=bool)
        for col, rc in enumerate(self.range_widgets):
            low, high = rc.current_range()
            mask &= (self._summarystats[:, col] >= low) & (self._summarystats[:, col] <= high)
        return mask

    # async / callback handlers
    def on_full_histograms_ready(self, results):
        self.hist_cache = results  # save it
        # Initial display: no reduced histograms
        for rc, hist in zip(self.range_widgets, results):
            rc.make_histogram({
                "bins": hist["bins"],
                "full": hist["full"],
                "reduced": None
            })
        self.n_update.setText(f"n = {sum(results[0]['full'])}")
        self.btn_compute.setEnabled(True)
        self.btn_compute.setText("Compute")

    def on_histograms_ready(self, results):
        for rc, hist_data in zip(self.range_widgets, results):
            rc.make_histogram(hist_data)
        self.btn_compute.setEnabled(True)
        self.btn_compute.setText("compute")
        if self.user_compute:
            self.n_update.setText(f"n = {sum(results[0]['reduced'])}")
            self.btn_save.setEnabled(True)
            self.btn_back.setEnabled(True)
            self.btn_switch.setEnabled(True)

    # prepare data for saving 
    def sample_subset_for_saving(self):
        logging.debug("ToolC.sample_subset_for saving")
        mask = self.compute_shared_mask()  
        n = int(self.sample_n.value())
        subset_data = self._summarystats[mask]
        subset_prior = self._priorsamples[mask]
        if n < len(subset_data):
            ints = random.sample(range(1, len(subset_data)), n)
            subset_data_samples = subset_data[ints]
            subset_prior_samples = subset_prior[ints]
        elif n == len(subset_data):
            subset_data_samples = subset_data
            subset_prior_samples = subset_prior
        else:
            print(f"Warning: wanted number of models {n} exceeds number of matching samples, can only return {len(subset_data)} matching samples.")
            subset_data_samples = subset_data
            subset_prior_samples = subset_prior
        return subset_data_samples, subset_prior_samples
