import logging
import numpy as np
import random

from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPixmap
from PySide6.QtCore import QLocale, Signal, QThread

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

from ampullary_ui.ui import Ui_ModelCatalog
from ampullary_ui.utils import get_outputfolder, save_data, save_features, save_figure, load_labels, save_sampled_subset
from ampullary_ui.signals import SimulatorSignals
from ampullary_ui.plotting.plot_cell import plot_cell
from ampullary_ui.computations.controller_functions import simulate_from_input_params
from ampullary_ui.gui.customcombienationwidget import RangeCombine

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


class ModelCatalog(QWidget):
    generating = Signal(str)
    generation_done = Signal(str)
    processing = Signal(str, float)
    processing_done = Signal(str, float)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._ui = Ui_ModelCatalog()
        self._ui.setupUi(self)
        self.full_worker = None  # Initialize worker variables
        self.reduced_worker = None

        self._user_compute = False
        self._summarystats = None
        self._priorsamples = None
        self._hist_cache = None
        self._titles = load_labels()['feature_labels']
        self._range_widgets = []

        self._compute_btn = self._ui.compute_btn
        self._save_btn = self._ui.save_btn
        self._name_edit = self._ui.name_prefix_edit
        self._range_widget_container = self._ui.placeholder
        self._samples_spinbox = self._ui.sample_spinbox
        self._update_label = self._ui.gm_n_update

        self._setup_defaults()
        self._define_stuff()
        self._compute_btn.clicked.connect(self._on_compute)
        self._save_btn.clicked.connect(self._on_save)
        # QTimer.singleShot(0, self.compute_initial_histograms)

    def _setup_defaults(self):
        self._save_btn.setEnabled(False)
        self._name_edit.setText("subset_001")
        self._samples_spinbox.setMinimum(1)
        self._samples_spinbox.setMaximum(12_000_000)
        self._samples_spinbox.setValue(100)

    def _define_stuff(self): 
        self._mins = [30.0, 0.0, -0.75, 0.0, 0.0, 0.0, 0.0, 0.0, 3.66,
                      0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        self._maxs = [250.0, 1.0, 1.0, 200, 1.0, 1.0, 0.4, 50, 150.0,
                      1000.0, 2000.0, 3000.0, 400, 100.0, 30.0, 50.0, 100.0]
        self._bin_specs = { }
        # Assign 200 to keys 0, and 1 to 6, and 9 to 13
        for k in [0] + list(range(1, 7)) + list(range(9, 14)):
            self._bin_specs[k] = 200
        # Assign 'numerical' to keys 7, 8, 14, 15, 16 (frequency features)
        for k in [7, 8, 14, 15, 16]:
            self._bin_specs[k] = "numerical"

        self._decimals = np.zeros(len(self._mins))
        self._steps = np.zeros(len(self._mins))
        for k in [1,2] + list(range(4, 7)):
            self._steps[k] = 0.01
            self._decimals[k] = 2
        for k in [0, 3] + list(range(7, 16)):
            self._steps[k] = 1.0
            self._decimals[k] = 0

    def set_data(self, summarystats, priorsamples):
        """
        Set data for processing and initialize histogram widgets.
        This method receives summary statistics and prior samples, stores them,
        creates range selection widgets, and computes initial histograms for visualization.
        Args:
            summarystats: Summary statistics data to be stored and processed.
            priorsamples: Prior samples data to be stored and processed.
        Emits:
            processing: Signal with status message "Data processing..." and progress value 0.0.
        """

        logging.debug("ToolC.set_data: received data")
        self.processing.emit("Data processing...", 0.0)
        self._summarystats = summarystats
        self._priorsamples = priorsamples
        self._insert_range_widgets(3)
        self._compute_initial_histograms()

    def _insert_range_widgets(self, cols):
        self._range_widgets = []
        layout = self._range_widget_container.layout()
        if layout is None:
            raise RuntimeError("gm_placeholder_widget has no layout in Qt Designer!")
        for col in range(17):
            rc = RangeCombine(data=self._summarystats[:, col],
                              min_value=self._mins[col],
                              max_value=self._maxs[col], 
                              bin_specs=self._bin_specs[col],
                              decimals=self._decimals[col],
                              step=self._steps[col],
                              label=self._titles[col])
            self._range_widgets.append(rc)
        for i, rc in enumerate(self._range_widgets):
            row_grid = i // cols
            col_grid = i % cols
            layout.addWidget(rc, row_grid, col_grid)

    def _compute_initial_histograms(self):
        self.processing.emit("Processing summary statistics ...", 0.5)

        if self._summarystats is None:
            return
        self._user_compute = False
        self._compute_btn.setEnabled(False)
        self._compute_btn.setText("loading…")

        self.full_worker = FullHistogramWorker(self._summarystats,
                                               self._mins, self._maxs,
                                               self._bin_specs)
        self.full_worker.finished.connect(self._on_full_histograms_ready)
        self.full_worker.finished.connect(self.full_worker.quit)  # Clean up thread when done
        self.full_worker.finished.connect(self.full_worker.deleteLater)
        self.full_worker.start()

    def _on_compute(self):
        self.generating.emit("Computing samples ...")
        self._user_compute = True
        self._compute_btn.setEnabled(False)
        self._compute_btn.setText("computing…")
        self._save_btn.setEnabled(False)
        mask = self._compute_shared_mask()
        self.reduced_worker = ReducedHistogramWorker(self._summarystats, mask,
                                                     self._hist_cache)
        self.reduced_worker.finished.connect(self._on_histograms_ready)
        self.reduced_worker.finished.connect(self.reduced_worker.quit)  # Clean up thread when done
        self.reduced_worker.finished.connect(self.reduced_worker.deleteLater)
        self.reduced_worker.start()

    def _on_save(self):
        output_folder = get_outputfolder()

        data_samples, prior_samples = self._sample_subset_for_saving()
        filename = self._name_edit.text().strip()
        save_sampled_subset(data_samples, prior_samples, output_folder, filename)
        self._save_btn.setText("save another set")

    def _compute_shared_mask(self):
        mask = np.ones(len(self._summarystats), dtype=bool)
        for col, rc in enumerate(self._range_widgets):
            low, high = rc.current_range()
            mask &= (self._summarystats[:, col] >= low) & (self._summarystats[:, col] <= high)
        return mask

    def _on_full_histograms_ready(self, results):
        self._hist_cache = results  # save it
        # Initial display: no reduced histograms
        for rc, hist in zip(self._range_widgets, results):
            rc.make_histogram({
                "bins": hist["bins"],
                "full": hist["full"],
                "reduced": None
            })
        self._update_label.setText(f"n = {sum(results[0]['full'])}")
        self._compute_btn.setEnabled(True)
        self._compute_btn.setText("Compute")
        self.generation_done.emit("Done.")
        self.processing_done.emit("Done.", 1.0)

    def _on_histograms_ready(self, results):
        for rc, hist_data in zip(self._range_widgets, results):
            rc.make_histogram(hist_data)
        self._compute_btn.setEnabled(True)
        self._compute_btn.setText("compute")
        if self._user_compute:
            self._update_label.setText(f"n = {sum(results[0]['reduced'])}")
            self._save_btn.setEnabled(True)
        self.generation_done.emit("Done.")

    def _sample_subset_for_saving(self):
        logging.debug("ModelCatalog.sample_subset_for saving")
        mask = self._compute_shared_mask()  
        n = int(self._samples_spinbox.value())
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
            logging.warning("Warning: wanted number of models %i exceeds number of matching samples, can only return %i matching samples.", n, len(subset_data))
            subset_data_samples = subset_data
            subset_prior_samples = subset_prior
        return subset_data_samples, subset_prior_samples
