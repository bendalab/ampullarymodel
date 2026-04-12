import logging
import numpy as np

from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtCore import Qt, Signal

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

from ampullary_ui.ui import Ui_ModelCatalogExplicit
from ampullary_ui.utils import get_outputfolder, load_labels, save_sampled_subset
from ampullary_ui.plotting.plot_distro import plot_samples


class ModelCatalogExplicit(QWidget):
    processing = Signal(str, float)
    processing_done = Signal(str, float)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._ui = Ui_ModelCatalogExplicit()
        self._ui.setupUi(self)
        self._canvas = None
        self._current_fig = None
        self._placeholder_canvas = None
        self._save_btn = self._ui.save_btn
        self._search_btn = self._ui.search_btn
        self._name_edit = self._ui.name_edit
        self._nsamples_spinbox = self._ui.samples_spinbox
        self._plot_container = self._ui.figure
        self._plot_layout = self._plot_container.layout()
        self._inputs = self._find_inputs()

        self._save_btn.setEnabled(False)
        self._name_edit.setText("subset_001")
        self._nsamples_spinbox.setMinimum(1)
        self._nsamples_spinbox.setMaximum(12_000_000) #!!!
        self._nsamples_spinbox.setValue(100)

        self._feature_labels = load_labels()['feature_labels']
        self._summarystats = None
        self._priorsamples = None
        self._near_data_samples = None
        self._near_prior_samples = None

        self._search_btn.clicked.connect(self._on_search)
        self._save_btn.clicked.connect(self._on_save)

    def _find_inputs(self):
        temp = []
        candidates = [name for name in self._ui.__dir__() if "_edit_" in name]
        for i in range(1, 18):
            stub = f"_edit_{i}"
            for c in candidates:
                if stub in c:
                    temp.append(getattr(self._ui, c))
                    candidates.remove(c)
        for inp in temp:
            inp.setPlaceholderText("None")
            inp.setAlignment(Qt.AlignRight)
            inp.setStyleSheet("""QLineEdit:placeholder{color: #888;}""") 

        return temp

    def set_data(self, summarystats, priorsamples):
        self.processing.emit("Processing data ...", 0.0)
        self._summarystats = summarystats
        self.processing.emit("Processing data ...", 0.5)
        self._priorsamples = priorsamples
        self._setup_placeholder_plot()
        self.processing_done.emit("Processing done.", 1.0)

    def _get_subset_values(self, sum_stats, prior_samples, values, n):
        if n > len(sum_stats): 
            raise ValueError(f"Error: wanted number of models {n} surpasses model catalog size of 12 Mio.")

        dims_to_use = np.where(~np.isnan(values))[0]
        if len(dims_to_use) == 0:
            #print("Warning: no valid choices provided, returning random samples.")
            nearest_idx = np.random.choice(sum_stats.shape[0], size=n, replace=False)
            nearest_sum_stats = sum_stats[nearest_idx]
            nearest_prior_samples = prior_samples[nearest_idx]
        else: 
            # cut down vals and sum stats to relevent dimentions 
            vals_sub = values[dims_to_use]
            sum_stats_sub = sum_stats[:, dims_to_use]
            # best needs to start relly high to be cut off
            best_dist = np.full(n, np.inf, dtype=np.float32)
            best_idx = np.full(n, -1, dtype=np.int64)
            # chunks to be able to run this with less RAM
            chunk_size = 500_000 
            for start in range(0, sum_stats.shape[0], chunk_size):
                stop = min(start + chunk_size, sum_stats.shape[0])
                block = sum_stats_sub[start:stop]
                # distange between wanted an have
                diff = block - vals_sub   
                dist2 = np.einsum('ij,ij->i', diff, diff) # distance without creating a giant temporary
                idx = np.argpartition(dist2, n)[:n]
                cand_dist = dist2[idx]
                cand_idx = idx + start
                # merge with current best
                all_dist = np.concatenate((best_dist, cand_dist))
                all_idx = np.concatenate((best_idx, cand_idx))
                # take n best fitting
                keep = np.argpartition(all_dist, n)[:n] # if same distance, will be 'random-ish' no need for random samples implementation (ask Jan if I am right)
                best_dist = all_dist[keep]
                best_idx = all_idx[keep]
            # final ordering
            order = np.argsort(best_dist)
            nearest_sum_stats = sum_stats[best_idx[order]]
            nearest_prior_samples = prior_samples[best_idx[order]]
        return nearest_sum_stats, nearest_prior_samples

    def _setup_placeholder_plot(self):
        values = np.array([100, 0.12]+[np.nan]*15)
        n = 100
        self._near_data_samples, self._near_prior_samples = self._get_subset_values(self._summarystats, self._priorsamples, values, n)
        fig = plot_samples(values, self._near_data_samples, self._feature_labels)
        self._current_fig = fig
        fig.text(0.5, 0.5, "EXAMPLE", fontsize=80, fontweight='bold', color='#44F9BD', alpha=0.6, ha='center',
                 va='center', rotation=40, zorder=10)

        self._placeholder_canvas = FigureCanvas(fig)
        self._placeholder_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._plot_layout.addWidget(self._placeholder_canvas)

    def _on_search(self):
        self._search_btn.setEnabled(False)
        self._search_btn.setText("Searching…")
        values = self._get_values_from_lines()
        n = int(self._nsamples_spinbox.value())
        self._near_data_samples, self._near_prior_samples = self._get_subset_values(self._summarystats, self._priorsamples, values, n)

        fig = plot_samples(values, self._near_data_samples, self._feature_labels)
        self._current_fig = fig
        # Display the figure
        self._show_simulation_figure()
        # enable again
        self._search_btn.setEnabled(True)
        self._search_btn.setText("Search samples")
        self._save_btn.setEnabled(True)

    def _on_save(self):
        output_folder = get_outputfolder()
        filename = self._name_edit.text().strip()
        save_sampled_subset(self._near_data_samples, self._near_prior_samples, output_folder, filename)
        self._save_btn.setEnabled(False)

    def _get_values_from_lines(self):
        vals_convert = np.full(len(self._inputs), np.nan, dtype=float)  # Initialize with NaNs
        for i, line in enumerate(self._inputs):
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

    def _show_simulation_figure(self):
        if hasattr(self, '_placeholder_canvas') and self._placeholder_canvas:
            self._plot_layout.removeWidget(self._placeholder_canvas)
            self._placeholder_canvas.deleteLater()
            self._placeholder_canvas = None
        # Remove old simulation canvas if needed
        if hasattr(self, '_canvas') and self._canvas:
            self._plot_layout.removeWidget(self._canvas)
            self._canvas.deleteLater()
            self._canvas = None
        # Add matplotlib new canvas for updated simulation figure
        self._canvas = FigureCanvas(self._current_fig)
        self._canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._plot_layout.addWidget(self._canvas)
