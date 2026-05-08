import logging
import time
import pandas as pd

from pathlib import Path

from PySide6.QtWidgets import QMainWindow, QLabel, QWidget, QTabWidget, QMessageBox
from PySide6.QtGui import QAction, QKeySequence, QIcon
from PySide6.QtCore import QTimer, Qt, QSize, QRunnable, Slot, QThreadPool, QSettings

# # Suppress Qt warning about missing tool_selection signal (manually connected in __init__)
# warnings.filterwarnings("ignore", message=".*QMetaObject::connectSlotsByName.*tool_selection.*")

from ampullary_ui.ui import Ui_MainWindow
from ampullary_ui.gui import SplashPage, StartPage, ModelCatalog, ModelCatalogExplicit
from ampullary_ui.gui.simulator import Simulator
from ampullary_ui.gui.populationsimulator import PopulationSimulator
from ampullary_ui.gui.modelgenerator import Modelgenerator
from ampullary_ui.gui.populaitiongenerator import PopulationGenerator
from ampullary_ui.utils import get_outputfolder, read_output_folder, Tool
from ampullary_ui.dialogs import AboutDialog, HelpDialog, ModelSettingsDialog
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
        self._setup_animation()
        self.start_progress_animation()
        self._qsettings = QSettings()

        self._tool_registry = {}
        self._stack = self._ui.stack
        self.splash = SplashPage(self)
        self._stack.removeWidget(self._ui.stack.widget(0))
        self._register_tool(Tool.SPLASH, 0, self.splash)
        self._stack.setCurrentIndex(0)

        self.startpage = StartPage(self)
        self.startpage.tool_selection.connect(self._on_tool_selection)
        self._register_tool(Tool.START, 1, self.startpage)

        self._setup_simulator()
        self._setup_generator()
        self._setup_modelcatalog()

        self._create_actions()
        self._create_menu()
        self._create_toolbar()

        self._index = 0

        self._summarystats = None
        self._priorsamples = None
        priorsamples_value = self._qsettings.value("model/priorsamples", "") or ""
        summarystats_value = self._qsettings.value("model/summarystats", "") or ""
        self._priorsamplesfile = Path(str(priorsamples_value))
        self._summarystatsfile = Path(str(summarystats_value))
        self._threadpool = QThreadPool()
        self._start_data_loader()


    def _setup_simulator(self):
        self.simulator = Simulator()
        self.simulator.simulating.connect(self._on_process_busy)
        self.simulator.simulation_done.connect(self._on_process_done)

        self.pop_simulator = PopulationSimulator(self)
        self.pop_simulator.simulating.connect(self._on_process_busy)
        self.pop_simulator.simulation_done.connect(self._on_process_done)

        self.stabs = QTabWidget(self)
        self.stabs.setTabPosition(QTabWidget.TabPosition.West)
        self.stabs.addTab(self.simulator, "Single cell")
        self.stabs.addTab(self.pop_simulator, "Population")

        self._register_tool(Tool.SIMULATOR, 2, self.stabs)

    def _setup_generator(self):
        self.generator = Modelgenerator(self)
        self.generator.simulating.connect(self._on_process_busy)
        self.generator.simulation_done.connect(self._on_process_done)
        self.generator.generating.connect(self._on_process_busy)
        self.generator.generating_done.connect(self._on_process_done)

        self.pop_generator = PopulationGenerator(self)

        self.gtabs = QTabWidget(self)
        self.gtabs.setTabPosition(QTabWidget.TabPosition.West)
        self.gtabs.addTab(self.generator, "Single cell")
        self.gtabs.addTab(self.pop_generator, "Population")

        self._register_tool(Tool.MODELGENERATOR, 3, self.gtabs)

    def _setup_modelcatalog(self):
        self.modelpicker = ModelCatalog(self)
        self.modelpicker.generating.connect(self._on_process_busy)
        self.modelpicker.generation_done.connect(self._on_process_done)
        self.modelpicker.processing.connect(self._on_dataprogress)
        self.modelpicker.processing_done.connect(self._on_dataprogress)

        self.modelpicker_exp = ModelCatalogExplicit(self)
        self.modelpicker_exp.processing.connect(self._on_process_busy)
        self.modelpicker_exp.processing.connect(self._on_dataprogress)
        self.modelpicker_exp.processing_done.connect(self._on_process_done)
        self.modelpicker_exp.processing_done.connect(self._on_dataprogress)

        self.ctabs = QTabWidget(self)
        self.ctabs.setTabPosition(QTabWidget.TabPosition.West)
        self.ctabs.addTab(self.modelpicker, "Select by range")
        self.ctabs.addTab(self.modelpicker_exp, "Select by feature")
        self._register_tool(Tool.MODELCATALOG, 4, self.ctabs)

    def _register_tool(self, tool: Tool, index: int, widget: QWidget):
        if tool in self._tool_registry:
            logging.warning("Trying to register tool %s to index %i which is already registered.", tool.name, index)
        self._tool_registry[tool] = index
        self._stack.insertWidget(index, widget)

    def _create_actions(self):
        self._quit_action = QAction(QIcon(":/icons/exit"), "Quit", parent=self)
        self._quit_action.setStatusTip("Close current file and quit")
        self._quit_action.setShortcut(QKeySequence("Ctrl+q"))
        self._quit_action.triggered.connect(self._on_exit_request)

        self._simulator_action = QAction("Simulator", parent=self)
        self._simulator_action.setStatusTip("Run simulator tool")
        self._simulator_action.setShortcut(QKeySequence("F2"))
        self._simulator_action.triggered.connect(lambda: self._on_tool_selection(Tool.SIMULATOR))

        self._modelgenerator_action = QAction("Model generator", parent=self)
        self._modelgenerator_action.setStatusTip("Generate models")
        self._modelgenerator_action.setShortcut(QKeySequence("F3"))
        self._modelgenerator_action.triggered.connect(lambda: self._on_tool_selection(Tool.MODELGENERATOR))

        self._modelcatalogue_action = QAction("Model catalogue", parent=self)
        self._modelcatalogue_action.setStatusTip("Select models based on the training datasets")
        self._modelcatalogue_action.setShortcut(QKeySequence("F4"))
        self._modelcatalogue_action.triggered.connect(lambda: self._on_tool_selection(Tool.MODELCATALOG))

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

        self._manage_model_action = QAction("manage model", parent=self)
        self._manage_model_action.setStatusTip("Manage the SBI network and other files")
        self._manage_model_action.setToolTip("Manage model files.")
        self._manage_model_action.setEnabled(True)
        self._manage_model_action.triggered.connect(self._on_manage_model)

        self._help_action = QAction(QIcon(":/icons/help"), "help", parent=self)
        self._help_action.setStatusTip("Show help dialog")
        self._help_action.setShortcut(QKeySequence("F1"))
        self._help_action.setEnabled(True)
        self._help_action.triggered.connect(self._on_help)

    def _create_menu(self):
        file_menu = self._ui.menubar.addMenu("&File")
        file_menu.addAction(self._set_outfolder_action)
        file_menu.addAction(self._manage_model_action)
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
        self._ui.toolbar.setStyleSheet("QToolButton{min-height: 30px;}")

        self._ui.toolbar.addAction(self._home_action)
        self._ui.toolbar.addAction(self._quit_action)
        self._ui.toolbar.addAction(self._help_action)
        self._ui.toolbar.addSeparator()
        self._ui.toolbar.addAction(self._simulator_action)
        self._ui.toolbar.addAction(self._modelgenerator_action)
        self._ui.toolbar.addAction(self._modelcatalogue_action)

    def _on_data_loaded(self):
        self._summarystats, self._priorsamples = self._dataloader.data
        logging.debug("Data loader done")
        self._on_dataprogress("Processing data ...", 0.0)
        self.modelpicker.set_data(self._summarystats, self._priorsamples)
        logging.info("data sent to modelpikcer")
        logging.info("Sending data to modelpicker expl.")
        self.modelpicker_exp.set_data(self._summarystats, self._priorsamples)
        logging.info("ModelPicker_expl done")
        time.sleep(1.5)
        self.stop_progress_animation()
        self._ui.stack.setCurrentIndex(1)

    def _on_dataprogress(self, msg, p):
        self.splash.message(msg)

    def _on_setoutputfolder(self):
        get_outputfolder()

    def _setup_animation(self, stepsize=1, maxsteps=40):
        self._status_label = QLabel()
        fish_right = "><(((°>"
        fish_left = "<°)))><"
        self.pattern = []
        for i in range(maxsteps):
            left = " " * i * stepsize
            right = " " * (maxsteps-i) * stepsize
            self.pattern.append(f"{left}{fish_right}{right}")
        for i in range(maxsteps, 0, -1):
            self.pattern.append(f"{" " * i * stepsize}{fish_left}{" " * (maxsteps - i) * stepsize}")
        self._index = 0
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_animation)
        self._ui.statusbar.addPermanentWidget(self._status_label)
        self._status_label.hide()

    def _on_manage_model(self):
        dlg = ModelSettingsDialog(self)
        dlg.show()

    def _start_data_loader(self):
        invalid_reasons = []
        if len(str(self._summarystatsfile)) == 0 or str(self._summarystatsfile) == ".":
            invalid_reasons.append("summary statistics file is not set")
        elif not self._summarystatsfile.exists():
            invalid_reasons.append(f"summary statistics file does not exist: {self._summarystatsfile}")

        if len(str(self._priorsamplesfile)) == 0 or str(self._priorsamplesfile) == ".":
            invalid_reasons.append("prior samples file is not set")
        elif not self._priorsamplesfile.exists():
            invalid_reasons.append(f"prior samples file does not exist: {self._priorsamplesfile}")

        if invalid_reasons:
            self.stop_progress_animation()
            self._ui.stack.setCurrentIndex(1)
            details = "\n".join(invalid_reasons)
            QMessageBox.critical(
                self,
                "Model files missing",
                f"Model data files are missing or invalid:\n{details}\n\nPlease configure them in Manage model.",
            )
            self._manage_model_action.trigger()
            return

        try:
            self._dataloader = DataLoader(self._summarystatsfile,
                                          self._priorsamplesfile)
        except FileNotFoundError as exc:
            self.stop_progress_animation()
            self._ui.stack.setCurrentIndex(1)
            QMessageBox.critical(
                self,
                "Model files missing",
                f"{exc}\n\nPlease configure them in Manage model.",
            )
            self._manage_model_action.trigger()
            return

        self._dataloader._signals.finished.connect(self._on_data_loaded)
        self._dataloader._signals.progress.connect(self._on_dataprogress)
        self._threadpool.start(self._dataloader)

    def start_progress_animation(self):
        """ Starts the progress animation """
        self._status_label.show()
        self._timer.start(100)

    def stop_progress_animation(self):
        """ Stops the progress animation """
        self._timer.stop()
        self._status_label.hide()

    def _update_animation(self):
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
    def _on_tool_selection(self, tool: Tool):
        if tool not in self._tool_registry:
            logging.error("Cannot switch to tool %s", tool.name)
            return
        self._stack.setCurrentIndex(self._tool_registry[tool])
        logging.info("A tool was selected %s", tool)

    def _go_home(self):
        self._stack.setCurrentWidget(self.startpage)

    def _on_about(self):
        about_dlg = AboutDialog(self)
        about_dlg.show()

    def _on_help(self):
        help_dlg = HelpDialog(self)
        help_dlg.show()

    def _on_exit_request(self):
        logging.info("Exit request, closing application now!")
        self.close()
