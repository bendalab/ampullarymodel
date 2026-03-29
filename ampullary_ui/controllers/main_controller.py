import logging
import pandas as pd

from pathlib import Path
from PySide6.QtWidgets import QWidget, QSizePolicy, QLabel, QToolBar, QMenuBar
from PySide6.QtCore import QEvent, QTimer, QUrl, Qt, QSize, QRunnable, Slot, QThreadPool
from PySide6.QtGui import QPixmap, QDesktopServices, QAction, QKeySequence, QIcon

from ampullary_ui.controllers.simulator import Simulator
from ampullary_ui.controllers.tool_b_controller import ToolBController
from ampullary_ui.controllers.tool_c_controller import ToolCController
from ampullary_ui.controllers.tool_d_controller import ToolDController
from ampullary_ui.controllers.populationsimulator import PopulationSimulator
from ampullary_ui.controllers.tool_b_extantion import ToolBExtention
from ampullary_ui.plotting.plot_cell import plot_cell
from ampullary_ui.utils import get_outputfolder, load_labels, read_output_folder
from ampullary_ui.dialogs import AboutDialog, HelpDialog

from ampullary_ui.signals import DataReaderSignals
print("Main:imports done")

class DataLoader(QRunnable):
    def __init__(self, summaryfile:Path, priorfile:Path) -> None:
        super().__init__()
        if not summaryfile.exists() or not priorfile.exists():
            raise FileNotFoundError(f"Either the summary stats, or the prior samples are not found! {summaryfile}, {priorfile}")
        self._sfile = summaryfile
        self._pfile = priorfile
        self._signals = DataReaderSignals()
        self._summarystats = None
        self._priorsamples = None

    @Slot()
    def run(self):
        self._signals.progress.emit("Loading summary stats...", 0.3)
        self._summarystats = pd.read_hdf(self._sfile, key="table").to_numpy()

        self._signals.progress.emit("Loading prior stats...", 0.6)
        self._priorsamples = pd.read_hdf(self._pfile, key="table").to_numpy()

        self._signals.progress.emit("Done", 1.0)
        self._signals.finished.emit(True)

    @property
    def data(self):
        return self._summarystats, self._priorsamples


class MainController(QWidget):
    def __init__(self, window):
        super().__init__()
        logging.info(f"MainController: init")
        self._window = window
        self._stacked = None
        self._timer = None
        self._status_label = None
        self._summarystats = None
        self._priorsamples = None
        self._threadpool = QThreadPool()

        self._find_widgets()
        self._setup_animation()

        self._example_fig = self._load_example_fig()
        labels = load_labels()
        self._dataloader = DataLoader(Path.cwd() / "source" / "summary_statistics.h5",
                                      Path.cwd() / "source" / "prior_samples.h5")
        self._dataloader._signals.finished.connect(self._on_data_loaded)
        self._dataloader._signals.progress.connect(self._on_dataprogress)

        logging.debug(f"MainController: initialize tools")
        self._simulator = Simulator(self, labels['feature_labels_casual'])
        logging.debug(f"MainController: toolA initialized")
        self.toolB = ToolBController(self, labels['parameter_labels_casual'],
                                     labels['feature_labels_casual'])
        logging.debug(f"MainController: toolB initialized")
        self.toolC = ToolCController(self._window, labels['feature_labels_casual'])
        logging.debug(f"MainController: toolC initialized")
        self.toolD = ToolDController(self._window, labels['feature_labels'])
        logging.debug(f"MainController: toolD initialized")

        self._pop_simulator = PopulationSimulator(self)
        self.toolB_ex = ToolBExtention(self)
        logging.debug(f"MainController: extensions initialized")

        self._setup_images()
        self._connect_navigation()
        self._window.description_1.anchorClicked.connect(self.open_example)

        self._create_actions()
        self._create_menu()
        self._create_toolbar()
        self._stacked.setCurrentWidget(self._window.startpage)
        self.setEnabled(False)
        logging.debug(f"MainController: initialized")
        self.start_progress_animation()
        self._threadpool.start(self._dataloader)

    def _on_data_loaded(self):
        self.stop_progress_animation()
        self._summarystats, self._priorsamples = self._dataloader.data
        self.setEnabled(True)
        logging.debug("Data loader done")
        self.toolC.set_data(self._summarystats, self._priorsamples)
        self.toolD.set_data(self._summarystats, self._priorsamples)

    def _on_dataprogress(self, msg, p):
        print("load progress", msg,  p)

    def _find_widgets(self):
        self._stacked = self._window.findChild(QWidget, "stackedWidget_main")
        self._menubar = self._window.findChild(QMenuBar, "menubar")
        self._toolbar = self._window.findChild(QToolBar, "toolbar")

    def _create_actions(self):
        self._quit_action = QAction(QIcon(":/icons/exit"), "Quit", parent=self._window)
        self._quit_action.setStatusTip("Close current file and quit")
        self._quit_action.setShortcut(QKeySequence("Ctrl+q"))
        self._quit_action.triggered.connect(self.cleanup_and_close)

        self._simulator_action = QAction("Simulator", parent=self._window)
        self._simulator_action.setStatusTip("Run simulator tool")
        self._simulator_action.setShortcut(QKeySequence("F2"))
        self._simulator_action.triggered.connect(self._run_simulator)

        self._modelgenerator_action = QAction("Model generator", parent=self._window)
        self._modelgenerator_action.setStatusTip("Generate models")
        self._modelgenerator_action.setShortcut(QKeySequence("F3"))
        self._modelgenerator_action.triggered.connect(self._run_modelgenerator)

        self._modelcatalogue_action = QAction("Model catalog", parent=self._window)
        self._modelcatalogue_action.setStatusTip("Select models based on the training datasets")
        self._modelcatalogue_action.setShortcut(QKeySequence("F4"))
        self._modelcatalogue_action.triggered.connect(self._run_modelpicker)

        self._home_action = QAction(QIcon(":/icons/home"), "Home")
        self._home_action.setStatusTip("Back to the start page")
        self._home_action.setToolTip("Back to the start page")
        self._home_action.setEnabled(True)
        self._home_action.setShortcut(QKeySequence("Esc"))
        self._home_action.triggered.connect(self._go_home)

        self._about_action = QAction("about")
        self._about_action.setStatusTip("Show about dialog")
        self._about_action.setEnabled(True)
        self._about_action.triggered.connect(self._on_about)

        self._set_outfolder_action = QAction("set output folder")
        self._set_outfolder_action.setStatusTip(str(read_output_folder))
        self._set_outfolder_action.setToolTip("Define the output folder")
        self._set_outfolder_action.setEnabled(True)
        self._set_outfolder_action.triggered.connect(self._on_setoutputfolder)

        self._help_action = QAction(QIcon(":/icons/help"), "help")
        self._help_action.setStatusTip("Show help dialog")
        self._help_action.setShortcut(QKeySequence("F1"))
        self._help_action.setEnabled(True)
        self._help_action.triggered.connect(self._on_help)

    def _create_menu(self):
        file_menu = self._menubar.addMenu("&File")
        file_menu.addAction(self._set_outfolder_action)
        file_menu.addSeparator()
        file_menu.addAction(self._quit_action)

        tools_menu = self._menubar.addMenu("&Tools")
        tools_menu.addAction(self._simulator_action)
        tools_menu.addAction(self._modelgenerator_action)
        tools_menu.addAction(self._modelcatalogue_action)

        help_menu = self._menubar.addMenu("&Help")
        help_menu.addAction(self._about_action)
        help_menu.addAction(self._help_action)

        # menus = {"File": file_menu, "Tools": tools_menu}
        # for k in self._cw.menuActions:
        #     actions = self._cw.menuActions[k]
        #     if k in menus:
        #         menu = menus[k]
        #     else:
        #         menu = menu_bar.addMenu(k)
        #     for a in actions:
        #         menu.addAction(a)
        # self.setMenuBar(self._menu_bar)

    def _create_toolbar(self):
        self._toolbar.setAllowedAreas(Qt.ToolBarArea.TopToolBarArea)
        self._toolbar.setFloatable(False)
        self._toolbar.setMovable(False)
        self._toolbar.setIconSize(QSize(25, 25))

        self._toolbar.addAction(self._home_action)
        self._toolbar.addAction(self._quit_action)
        self._toolbar.addAction(self._help_action)
        self._toolbar.addSeparator()
        self._toolbar.addAction(self._simulator_action)
        self._toolbar.addSeparator()
        self._toolbar.addAction(self._modelgenerator_action)
        self._toolbar.addSeparator()
        self._toolbar.addAction(self._modelcatalogue_action)

    def cleanup_and_close(self):
        logging.info("Cleanup and close!")
        """Stop all running threads before closing the application."""
        # # Stop ToolA thread
        # if hasattr(self._simulator, 'sim_thread') and self._simulator.sim_thread is not None:
        #     if self._simulator.sim_thread.isRunning():
        #         self._simulator.sim_thread.quit()
        #         # self._simulator.sim_thread.wait()
        
        # Stop ToolB thread
        if hasattr(self.toolB, 'sim_thread') and self.toolB.sim_thread is not None:
            if self.toolB.sim_thread.isRunning():
                self.toolB.sim_thread.quit()
                self.toolB.sim_thread.wait()
        
        # Stop ToolA Extension thread
        if hasattr(self._pop_simulator, 'sim_thread') and self._pop_simulator.sim_thread is not None:
            if self._pop_simulator.sim_thread.isRunning():
                self._pop_simulator.sim_thread.quit()
                self._pop_simulator.sim_thread.wait()
        
        # Stop ToolB Extension thread
        if hasattr(self.toolB_ex, 'sim_thread') and self.toolB_ex.sim_thread is not None:
            print(self.toolB_ex.sim_thread is None)
            if self.toolB_ex.sim_thread.isRunning():
                self.toolB_ex.sim_thread.quit()
                self.toolB_ex.sim_thread.wait()
        
        # Stop ToolC workers (histogram workers)
        # if hasattr(self.toolC, 'full_worker') and self.toolC.full_worker is not None:
        #     from IPython import embed
        #     embed()
        #     if self.toolC.full_worker.isRunning():
        #         self.toolC.full_worker.quit()
        #         self.toolC.full_worker.wait()
        if hasattr(self.toolC, 'reduced_worker') and self.toolC.reduced_worker is not None:
            if self.toolC.reduced_worker.isRunning():
                self.toolC.reduced_worker.quit()
                self.toolC.reduced_worker.wait()
        
        # Accept the close event
        #event.accept()
        

    def _on_setoutputfolder(self):
        get_outputfolder()

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

    def load_data(self):
        pwd = Path.cwd()
        logging.info("loading summary stats")
        filepath = pwd / "source" / "summary_statistics.h5"
        sum_stats = pd.read_hdf(filepath, key="table")
        logging.info("loading prior samples")

        filepath = pwd / "source" / "prior_samples.h5"
        prior_samples = pd.read_hdf(filepath, key="table")
        logging.info("loading stuff done")
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

    def _run_simulator(self):
        self._stacked.setCurrentWidget(self._window.simulate_cell)
        self._simulator._redraw_figure()

    def _run_modelgenerator(self):
        self._stacked.setCurrentWidget(self._window.create_model)
        self.toolB.redraw_figure()

    def _run_modelpicker(self):
        self._stacked.setCurrentWidget(self._window.get_model)

    def _go_home(self):
        self._stacked.setCurrentWidget(self._window.startpage)

    def _on_about(self):
        about = AboutDialog(self)
        about.show()

    def _on_help(self):
        help = HelpDialog(self)
        help.show()

    # navigation
    def _connect_navigation(self):
        # ToolA navigation
        self._window.button_to_sc.clicked.connect(self._run_simulator)
        self._window.sc_back_to_main.clicked.connect(lambda: self._stacked.setCurrentWidget(self._window.startpage))
        self._window.sc_table_version.clicked.connect(lambda: self._stacked.setCurrentWidget(self._window.table_sim)) 
        # ToolB navigation
        self._window.button_to_cm.clicked.connect(self._run_modelgenerator)
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
        self._window.ts_to_single.clicked.connect(self._run_simulator)
        # ToolB population navigation
        self._window.tc_back_to_main.clicked.connect(lambda: self._stacked.setCurrentWidget(self._window.startpage))
        self._window.tc_to_single.clicked.connect(self._run_modelgenerator)

    def exit_request(self):
        print("exit request")
        try:
            self.cleanup_and_close()
            print("closing now!")
            self.close()
        except Exception as e:
            print(e)
