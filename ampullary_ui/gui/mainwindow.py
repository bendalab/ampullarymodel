import logging
import pandas as pd
import warnings

from pathlib import Path

from PySide6.QtWidgets import QMainWindow, QLabel, QWidget
from PySide6.QtGui import QPixmap, QAction, QKeySequence, QIcon
from PySide6.QtCore import QEvent, QTimer, QUrl, Qt, QSize, QRunnable, Slot, QThreadPool

# # Suppress Qt warning about missing tool_selection signal (manually connected in __init__)
# warnings.filterwarnings("ignore", message=".*QMetaObject::connectSlotsByName.*tool_selection.*")

from ampullary_ui.ui import Ui_MainWindow
from ampullary_ui.gui.splashpage import SplashPage
from ampullary_ui.gui.startpage import StartPage
from ampullary_ui.gui.simulator import Simulator
from ampullary_ui.utils import get_outputfolder, load_labels, read_output_folder, Tool
from ampullary_ui.dialogs import AboutDialog, HelpDialog
from ampullary_ui.signals import DataReaderSignals


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


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self._ui = Ui_MainWindow()
        self._ui.setupUi(self)

        self._tool_registry = {}

        self.splash = SplashPage(self)
        self._ui.stack.removeWidget(self._ui.stack.widget(0))
        self.register_tool(Tool.SPLASH, 0, self.splash)

        self.startpage = StartPage(self)
        self.startpage.tool_selection.connect(self.on_tool_selection)
        self.register_tool(Tool.START, 1, self.startpage)

        self.simulator = Simulator(self)
        self.register_tool(Tool.SIMULATOR, 2, self.simulator)
        self.simulator.simulating.connect(self._on_process_busy)
        self.simulator.simulation_done.connect(self._on_process_done)

        self._ui.stack.setCurrentIndex(0)

        self.splash.message("do this")
        self._create_actions()
        self._create_menu()
        self._create_toolbar()

        self._status_label = None
        self._index = 0

        self._summarystats = None
        self._priorsamples = None
        self._dataloader = DataLoader(Path.cwd() / "source" / "summary_statistics.h5",
                                      Path.cwd() / "source" / "prior_samples.h5")
        self._dataloader._signals.finished.connect(self._on_data_loaded)
        self._dataloader._signals.progress.connect(self._on_dataprogress)
        self._threadpool = QThreadPool()

        self._setup_animation()
        self.start_progress_animation()
        self._threadpool.start(self._dataloader)

    def register_tool(self, tool: Tool, index: int, widget: QWidget):
        if tool in self._tool_registry:
            logging.warning("Trying to register tool %s to index %i which is already registered.", tool.name, index)
        self._tool_registry[tool] = index
        self._ui.stack.insertWidget(index, widget)

    def _create_actions(self):
        self._quit_action = QAction(QIcon(":/icons/exit"), "Quit", parent=self)
        self._quit_action.setStatusTip("Close current file and quit")
        self._quit_action.setShortcut(QKeySequence("Ctrl+q"))
        self._quit_action.triggered.connect(self._on_exit_request)

        self._simulator_action = QAction("Simulator", parent=self)
        self._simulator_action.setStatusTip("Run simulator tool")
        self._simulator_action.setShortcut(QKeySequence("F2"))
        self._simulator_action.triggered.connect(self._run_simulator)

        self._modelgenerator_action = QAction("Model generator", parent=self)
        self._modelgenerator_action.setStatusTip("Generate models")
        self._modelgenerator_action.setShortcut(QKeySequence("F3"))
        self._modelgenerator_action.triggered.connect(self._run_modelgenerator)

        self._modelcatalogue_action = QAction("Model catalog", parent=self)
        self._modelcatalogue_action.setStatusTip("Select models based on the training datasets")
        self._modelcatalogue_action.setShortcut(QKeySequence("F4"))
        self._modelcatalogue_action.triggered.connect(self._run_modelpicker)

        self._home_action = QAction(QIcon(":/icons/home"), "Home", parent=self)
        self._home_action.setStatusTip("Back to the start page")
        self._home_action.setToolTip("Back to the start page")
        self._home_action.setEnabled(True)
        self._home_action.setShortcut(QKeySequence("Esc"))
        self._home_action.triggered.connect(self._go_home)

        self._about_action = QAction("about", parent=self)
        self._about_action.setStatusTip("Show about dialog")
        self._about_action.setEnabled(True)
        self._about_action.triggered.connect(self._on_about)

        self._set_outfolder_action = QAction("set output folder", parent=self)
        self._set_outfolder_action.setStatusTip(str(read_output_folder))
        self._set_outfolder_action.setToolTip("Define the output folder")
        self._set_outfolder_action.setEnabled(True)
        self._set_outfolder_action.triggered.connect(self._on_setoutputfolder)

        self._help_action = QAction(QIcon(":/icons/help"), "help", parent=self)
        self._help_action.setStatusTip("Show help dialog")
        self._help_action.setShortcut(QKeySequence("F1"))
        self._help_action.setEnabled(True)
        self._help_action.triggered.connect(self._on_help)

    def _create_menu(self):
        file_menu = self._ui.menubar.addMenu("&File")
        file_menu.addAction(self._set_outfolder_action)
        file_menu.addSeparator()
        file_menu.addAction(self._quit_action)

        tools_menu = self._ui.menubar.addMenu("&Tools")
        tools_menu.addAction(self._simulator_action)
        tools_menu.addAction(self._modelgenerator_action)
        tools_menu.addAction(self._modelcatalogue_action)

        help_menu = self._ui.menubar.addMenu("&Help")
        help_menu.addAction(self._about_action)
        help_menu.addAction(self._help_action)

    def _create_toolbar(self):
        self._ui.toolbar.setAllowedAreas(Qt.ToolBarArea.TopToolBarArea)
        self._ui.toolbar.setFloatable(False)
        self._ui.toolbar.setMovable(False)
        self._ui.toolbar.setIconSize(QSize(25, 25))

        self._ui.toolbar.addAction(self._home_action)
        self._ui.toolbar.addAction(self._quit_action)
        self._ui.toolbar.addAction(self._help_action)
        self._ui.toolbar.addSeparator()
        self._ui.toolbar.addAction(self._simulator_action)
        self._ui.toolbar.addSeparator()
        self._ui.toolbar.addAction(self._modelgenerator_action)
        self._ui.toolbar.addSeparator()
        self._ui.toolbar.addAction(self._modelcatalogue_action)

    def _on_data_loaded(self):
        self.stop_progress_animation()
        self._summarystats, self._priorsamples = self._dataloader.data
        self.setEnabled(True)
        logging.debug("Data loader done")
        # self.toolC.set_data(self._summarystats, self._priorsamples)
        # self.toolD.set_data(self._summarystats, self._priorsamples)
        self._ui.stack.setCurrentIndex(1)

    def _on_dataprogress(self, msg, p):
        self.splash.message(msg)

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
        self._ui.statusbar.addPermanentWidget(self._status_label)
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

    def _on_process_busy(self, msg):
        print(msg)
        self.start_progress_animation()

    def _on_process_done(self, msg):
        print(msg)
        self.stop_progress_animation()

    def _on_process_errored(self, msg):
        logging.error("Subprocess failed with message: %s", msg)
        self.stop_progress_animation()

    @Slot()
    def on_tool_selection(self, tool: Tool):
        if tool not in self._tool_registry:
            logging.error("Cannot switch to tool %s", tool.name)
            return
        self._ui.stack.setCurrentIndex(self._tool_registry[tool])
        print(f"A tool was selected {tool}")

    # def open_example(self, url: QUrl):
    #     rel_path = Path(url.toString())
    #     base_dir = Path(__file__).resolve().parent
    #     abs_path = (base_dir / rel_path).resolve()
    #     QDesktopServices.openUrl(QUrl.fromLocalFile(str(abs_path)))

    def _run_simulator(self):
        self._ui.stack.setCurrentWidget(self.simulator)
        # self.simulator._redraw_figure()
        pass

    def _run_modelgenerator(self):
        # self._stacked.setCurrentWidget(self._window.create_model)
        # self.toolB.redraw_figure()
        pass

    def _run_modelpicker(self):
        # self._stacked.setCurrentWidget(self._window.get_model)
        pass

    def _go_home(self):
        self._ui.stack.setCurrentWidget(self.startpage)

    def _on_about(self):
        about_dlg = AboutDialog(self)
        about_dlg.show()

    def _on_help(self):
        help_dlg = HelpDialog(self)
        help_dlg.show()

    def _on_exit_request(self):
        logging.info("Exit request, closing application now!")
        self.close()
