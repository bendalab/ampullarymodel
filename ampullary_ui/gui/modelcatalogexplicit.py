import logging
import numpy as np
import random

from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPixmap
from PySide6.QtCore import QLocale, Signal, QThread

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

from ampullary_ui.ui import Ui_ModelCatalogExplicit
from ampullary_ui.utils import get_outputfolder, save_data, save_features, save_figure, load_labels, save_sampled_subset
from ampullary_ui.signals import SimulatorSignals
from ampullary_ui.plotting.plot_cell import plot_cell
from ampullary_ui.computations.controller_functions import simulate_from_input_params
from ampullary_ui.controllers.customcombienationwidget import RangeCombine


class ModelCatalogExplicit(QWidget):
    
    def __init__(self, parent=None):
        super.__init__(parent)
        
        self._ui = Ui_ModelCatalogExplicit()
        self._ui.setupUi(self)
        self.canvas = None
        self.current_fig = None
        
        self._save_btn = self._ui.save_btn
        self._search_btn = self._ui.search_btn
        self._name_edit = self._ui.name_edit
        self._nsamples_spinbox = self._ui.samples_spinbox
        self._plot_container = self._ui.figure
        self._inputs = [self._ui.]
        self.setup_defaults()
        self.titles = load_labels()['feature_labels']
        self._summarystats = None
        self._priorsamples = None
        self.connect_signals()
        
    def set_data(self, summarystats, priorsamples):
        self._summarystats = summarystats
        self._priorsamples = priorsamples
        self.setup_placeholder_plot()
