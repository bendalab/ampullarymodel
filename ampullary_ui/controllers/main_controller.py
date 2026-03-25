import pandas as pd
import logging
print("IMPORTS 1")

from pathlib import Path
from PySide6.QtWidgets import QWidget, QSizePolicy, QLabel
from PySide6.QtCore import  QEvent, QTimer, QUrl
from PySide6.QtGui import QPixmap, QDesktopServices
print("IMPORTS 2")

print("IMPORT simulator")
from ampullary_ui.controllers.simulator import Simulator
print("IMPORT B")
from ampullary_ui.controllers.tool_b_controller import ToolBController
print("IMPORT C")
from ampullary_ui.controllers.tool_c_controller import ToolCController
print("IMPORT D")
from ampullary_ui.controllers.tool_d_controller import ToolDController
print("IMPORT a extra")
from ampullary_ui.controllers.tool_a_extantion import ToolAExtention
print("IMPORT b extra")
from ampullary_ui.controllers.tool_b_extantion import ToolBExtention
print("IMPORT plot cell")
from ampullary_ui.plotting.plot_cell import plot_cell
print("IMPORT labels")
from ampullary_ui.utils import load_labels
print("IMPORTS DONE")

class MainController:
    def __init__(self, window):
        #super().__init__()
        logging.info(f"MainController: init")
        self._window = window
        self._stacked = None
        self._timer = None
        self._status_label = None
        self._find_widgets()
        self._setup_animation()
        logging.debug(f"MainController: window setup done")
        self._data, self._prior_samples = self.load_data()
        logging.debug(f"MainController: load data")

        self._example_fig = self._load_example_fig()
        labels = load_labels()
        #self.toolA = ToolAController(self.window, self.example_fig, labels['feature_labels_casual']) 
        #self.toolB = ToolBController(self.window, self.example_fig, labels['parameter_labels_casual'], labels['feature_labels_casual'], main_controller=self)
        logging.debug(f"MainController: initialize tools")
        self._simulator = Simulator(self, labels['feature_labels_casual'])
        logging.debug(f"MainController: toolA initialized")
        self.toolB = ToolBController(self, labels['parameter_labels_casual'],
                                     labels['feature_labels_casual'])
        logging.debug(f"MainController: toolB initialized")
        self.toolC = ToolCController(self._window, self._data, self._prior_samples,
                                     labels['feature_labels_casual'])
        logging.debug(f"MainController: toolC initialized")
        self.toolD = ToolDController(self._window, self._data, self._prior_samples,
                                     labels['feature_labels'])
        logging.debug(f"MainController: toolD initialized")

        self.toolA_ex = ToolAExtention(self)
        self.toolB_ex = ToolBExtention(self)
        logging.debug(f"MainController: extensions initialized")

        self._setup_images()
        self._connect_navigation()
        self._window.description_1.anchorClicked.connect(self.open_example)
        # Setup cleanup on window close
        self._window.closeEvent = self.cleanup_and_close

    def _find_widgets(self):
        self._stacked = self._window.findChild(QWidget, "stackedWidget_main")

    def cleanup_and_close(self, event):
        """Stop all running threads before closing the application."""
        # Stop ToolA thread
        if hasattr(self._simulator, 'sim_thread') and self._simulator.sim_thread is not None:
            if self._simulator.sim_thread.isRunning():
                self._simulator.sim_thread.quit()
                self._simulator.sim_thread.wait()
        
        # Stop ToolB thread
        if hasattr(self.toolB, 'sim_thread') and self.toolB.sim_thread is not None:
            if self.toolB.sim_thread.isRunning():
                self.toolB.sim_thread.quit()
                self.toolB.sim_thread.wait()
        
        # Stop ToolA Extension thread
        if hasattr(self.toolA_ex, 'sim_thread') and self.toolA_ex.sim_thread is not None:
            if self.toolA_ex.sim_thread.isRunning():
                self.toolA_ex.sim_thread.quit()
                self.toolA_ex.sim_thread.wait()
        
        # Stop ToolB Extension thread
        if hasattr(self.toolB_ex, 'sim_thread') and self.toolB_ex.sim_thread is not None:
            if self.toolB_ex.sim_thread.isRunning():
                self.toolB_ex.sim_thread.quit()
                self.toolB_ex.sim_thread.wait()
        
        # Stop ToolC workers (histogram workers)
        if hasattr(self.toolC, 'full_worker') and self.toolC.full_worker is not None:
            if self.toolC.full_worker.isRunning():
                self.toolC.full_worker.quit()
                self.toolC.full_worker.wait()
        if hasattr(self.toolC, 'reduced_worker') and self.toolC.reduced_worker is not None:
            if self.toolC.reduced_worker.isRunning():
                self.toolC.reduced_worker.quit()
                self.toolC.reduced_worker.wait()
        
        # Accept the close event
        event.accept()

    # setup processing animation
    def _setup_animation(self):
        # Create status label and timer for animation
        self._status_label = QLabel()
        self.pattern = [
        " ><(((°>        ",
        "  ><(((°>       ",
        "   ><(((°>      ",
        "    ><(((°>     ",
        "     ><(((°>    ",
        "      ><(((°>   ",
        "       ><(((°>  ",
        "        ><(((°> ",
        "         ><(((°>",
        "         <°)))><",
        "        <°)))>< ",
        "       <°)))><  ",
        "      <°)))><   ",
        "     <°)))><    ",
        "    <°)))><     ",
        "   <°)))><      ",
        "  <°)))><       ",
        " <°)))><        "
        ]
        self._index = 0
        self._timer = QTimer()
        self._timer.timeout.connect(self.update_animation)
        self._window.statusBar().addPermanentWidget(self._status_label)
        self._status_label.hide()


    def start_progress_animation(self):
        self._status_label.show()
        self._timer.start(300)


    def stop_progress_animation(self):
        self._timer.stop()
        self._status_label.hide()


    def update_animation(self):
        self._status_label.setText(f"processing... {self.pattern[self._index]}")
        self._index = (self._index + 1) % len(self.pattern)
        

    def open_example(self, url: QUrl):
        rel_path = Path(url.toString())
        base_dir = Path(__file__).resolve().parent
        abs_path = (base_dir / rel_path).resolve()
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(abs_path)))


    # load data and other stuff
    def load_data(self):
        pwd = Path.cwd()
        filepath = pwd / "source" / "summary_statistics.h5"
        sum_stats = pd.read_hdf(filepath, key="table")
        filepath = pwd / "source" / "prior_samples.h5"
        prior_samples = pd.read_hdf(filepath, key="table")
        return sum_stats.to_numpy(), prior_samples.to_numpy()


    def _load_example_fig(self):
        # load cell model simulation plot data
        filepath = Path.cwd() / "examples" / "example_figures" / "base_example.pkl"
        example_base = pd.read_pickle(filepath)
        filepath = Path.cwd() / "examples" / "example_figures" / "stim_example.pkl"
        example_stim = pd.read_pickle(filepath)
        fig = plot_cell(example_base, example_stim)
        fig.text(0.5, 0.5, "EXAMPLE", fontsize=80, fontweight='bold', color='#44F9BD', alpha=0.6, ha='center', va='center', rotation=40, zorder=10)
        return fig

    # images startpage
    def _setup_images(self):
        for lbl in (self._window.picture_1, self._window.picture_2, self._window.picture_3):
            lbl.setMinimumSize(100, 100)
            lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._window.picture_1.setPixmap(QPixmap(":/examples/eqn"))
        self._window.picture_2.setPixmap(QPixmap(":/examples/get_model"))
        self._window.picture_3.setPixmap(QPixmap(":/examples/table"))
        self._window.sc_equation.setPixmap(QPixmap(":/examples/eqn2"))

    # keep figures visible
    def eventFilter(self, obj, event):
        if obj == self.toolA_page and event.type() == QEvent.Type.Show:
            # Call redraw in your ToolA controller
            self._simulator._redraw_figure()
        return super().eventFilter(obj, event)

    def show_toolA_page(self):
        self._stacked.setCurrentWidget(self._window.simulate_cell)
        self._simulator._redraw_figure()

    def show_toolB_page(self):
        self._stacked.setCurrentWidget(self._window.create_model)
        self.toolB.redraw_figure()

    # navigation
    def _connect_navigation(self):
        # ToolA navigation
        self._window.button_to_sc.clicked.connect(self.show_toolA_page)
        self._window.sc_back_to_main.clicked.connect(lambda: self._stacked.setCurrentWidget(self._window.startpage))
        self._window.sc_table_version.clicked.connect(lambda: self._stacked.setCurrentWidget(self._window.table_sim)) 
        # ToolB navigation
        self._window.button_to_cm.clicked.connect(self.show_toolB_page)
        self._window.cm_back_to_main.clicked.connect(lambda: self._stacked.setCurrentWidget(self._window.startpage))
        self._window.cm_table_version.clicked.connect(lambda: self._stacked.setCurrentWidget(self._window.table_gen)) 
        # ToolC navigation
        self._window.button_to_gm.clicked.connect(lambda: self._stacked.setCurrentWidget(self._window.get_model))
        self._window.gm_back_to_main.clicked.connect(lambda: self._stacked.setCurrentWidget(self._window.startpage))
        self._window.gm_switch_to_d.clicked.connect(lambda: self._stacked.setCurrentWidget(self._window.get_model_explicit))
        # ToolD navigation
        self._window.gme_back_to_main.clicked.connect(lambda: self._stacked.setCurrentWidget(self._window.startpage))
        self._window.gme_switch_to_c.clicked.connect(lambda: self._stacked.setCurrentWidget(self._window.get_model))
        # ToolA population navigation
        self._window.ts_back_to_main.clicked.connect(lambda: self._stacked.setCurrentWidget(self._window.startpage))
        self._window.ts_to_single.clicked.connect(self.show_toolA_page)
        # ToolB population navigation
        self._window.tc_back_to_main.clicked.connect(lambda: self._stacked.setCurrentWidget(self._window.startpage))
        self._window.tc_to_single.clicked.connect(self.show_toolB_page)
