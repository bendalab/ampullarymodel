import os
import json
import pandas as pd
from pathlib import Path
from PySide6.QtWidgets import QWidget, QSizePolicy, QProgressBar, QLabel
from PySide6.QtCore import  QEvent, QTimer, QUrl
from PySide6.QtGui import QPixmap, QDesktopServices

from ampullary_ui.controllers.tool_a_controller import ToolAController
from ampullary_ui.controllers.tool_b_controller import ToolBController
from ampullary_ui.controllers.tool_c_controller import ToolCController
from ampullary_ui.controllers.tool_d_controller import ToolDController
from ampullary_ui.controllers.tool_a_extantion import ToolAExtention
from ampullary_ui.controllers.tool_b_extantion import ToolBExtention
from ampullary_ui.plotting.plot_cell import plot_cell


class MainController:
    def __init__(self, window):
        #super().__init__()
        self.window = window
        self.window.setWindowTitle("TestToolAmpullary")
        self.stacked = self.window.findChild(QWidget, "stackedWidget_main")
        self.setup_animation()
        self.data, self.prior_samples = self.load_data()
        self.example_fig = self.load_example_fig()
        labels = self.load_labels()
        #self.toolA = ToolAController(self.window, self.example_fig, labels['feature_labels_casual']) 
        #self.toolB = ToolBController(self.window, self.example_fig, labels['parameter_labels_casual'], labels['feature_labels_casual'], main_controller=self)
        self.toolA = ToolAController(self, labels['feature_labels_casual']) 
        self.toolB = ToolBController(self, labels['parameter_labels_casual'], labels['feature_labels_casual'])
        self.toolC = ToolCController(self.window, self.data, self.prior_samples, labels['feature_labels_casual'])
        self.toolD = ToolDController(self.window, self.data, self.prior_samples, labels['feature_labels'])
        self.toolA_ex = ToolAExtention(self)
        self.toolB_ex = ToolBExtention(self)
        self.setup_images()
        self.connect_navigation()
        self.window.description_1.anchorClicked.connect(self.open_example)
        


    # setup processing animation
    def setup_animation(self):
        # Create status label and timer for animation
        self.status_label = QLabel()
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
        self.index = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_animation)
        self.window.statusBar().addPermanentWidget(self.status_label)
        self.status_label.hide()


    def start_progress_animation(self):
        self.status_label.show()
        self.timer.start(300)


    def stop_progress_animation(self):
        self.timer.stop()
        self.status_label.hide()


    def update_animation(self):
        self.status_label.setText(f"processing... {self.pattern[self.index]}")
        self.index = (self.index + 1) % len(self.pattern)
        

    def open_example(self, url: QUrl):
        rel_path = Path(url.toString())
        base_dir = Path(__file__).resolve().parent
        abs_path = (base_dir / rel_path).resolve()
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(abs_path)))


    # load data and other stuff
    def load_data(self):
        filepath = os.path.join("..", "source", "summary_statistics.h5")
        sum_stats = pd.read_hdf(filepath, key="table")
        filepath = os.path.join("..", "source", "prior_samples.h5")
        prior_samples = pd.read_hdf(filepath, key="table")
        return sum_stats.to_numpy(), prior_samples.to_numpy()


    def load_example_fig(self):
        # load cell model simulation plot data
        filepath = os.path.join("..", "examples", "example_figures", "base_example.pkl") 
        example_base = pd.read_pickle(filepath)
        filepath = os.path.join("..", "examples", "example_figures", "stim_example.pkl") 
        example_stim = pd.read_pickle(filepath)
        fig = plot_cell(example_base, example_stim)
        fig.text(0.5, 0.5, "EXAMPLE", fontsize=80, fontweight='bold', color='#44F9BD', alpha=0.6, ha='center', va='center', rotation=40, zorder=10)
        return fig


    def load_labels(self):
        filepath = os.path.join("general_helpers", "labels.json")
        with open(filepath, "r") as file:
            labels = json.load(file)
        file.close()
        return labels


    # images startpage
    def setup_images(self):
        for lbl in (self.window.picture_1, self.window.picture_2, self.window.picture_3):
            lbl.setMinimumSize(100, 100)
            lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        filepath1 = os.path.join("..", "examples", "example_figures", "equation.png")
        filepath2 = os.path.join("..", "examples", "example_figures", "getmodel_scetch.png")
        filepath3 = os.path.join("..", "examples", "example_figures", "table_scetch.png")
        filepath4 = os.path.join("..", "examples", "example_figures", "equation2.png") 

        pix1 = QPixmap(filepath1)
        pix2 = QPixmap(filepath2)
        pix3 = QPixmap(filepath3)
        pix4 = QPixmap(filepath4)

        self.window.picture_1.setPixmap(pix1)
        self.window.picture_2.setPixmap(pix2)
        self.window.picture_3.setPixmap(pix3)
        self.window.sc_equation.setPixmap(pix4)
    
    
    # keep figures visible      
    def eventFilter(self, obj, event):
        if obj == self.toolA_page and event.type() == QEvent.Type.Show:
            # Call redraw in your ToolA controller
            self.toolA.redraw_figure()
        return super().eventFilter(obj, event)


    def show_toolA_page(self):
        self.stacked.setCurrentWidget(self.window.simulate_cell)
        self.toolA.redraw_figure()


    def show_toolB_page(self):
        self.stacked.setCurrentWidget(self.window.create_model)
        self.toolB.redraw_figure()


    # navigation
    def connect_navigation(self):
        # ToolA navigation
        self.window.button_to_sc.clicked.connect(self.show_toolA_page)
        self.window.sc_back_to_main.clicked.connect(lambda: self.stacked.setCurrentWidget(self.window.startpage))
        self.window.sc_table_version.clicked.connect(lambda: self.stacked.setCurrentWidget(self.window.table_sim)) 
        # ToolB navigation
        self.window.button_to_cm.clicked.connect(self.show_toolB_page)
        self.window.cm_back_to_main.clicked.connect(lambda: self.stacked.setCurrentWidget(self.window.startpage))
        self.window.cm_table_version.clicked.connect(lambda: self.stacked.setCurrentWidget(self.window.table_gen)) 
        # ToolC navigation
        self.window.button_to_gm.clicked.connect(lambda: self.stacked.setCurrentWidget(self.window.get_model))
        self.window.gm_back_to_main.clicked.connect(lambda: self.stacked.setCurrentWidget(self.window.startpage))
        self.window.gm_switch_to_d.clicked.connect(lambda: self.stacked.setCurrentWidget(self.window.get_model_explicit))
        # ToolD navigation
        self.window.gme_back_to_main.clicked.connect(lambda: self.stacked.setCurrentWidget(self.window.startpage))
        self.window.gme_switch_to_c.clicked.connect(lambda: self.stacked.setCurrentWidget(self.window.get_model))
        # ToolA population navigation
        self.window.ts_back_to_main.clicked.connect(lambda: self.stacked.setCurrentWidget(self.window.startpage))
        self.window.ts_to_single.clicked.connect(self.show_toolA_page)
        # ToolB population navigation
        self.window.tc_back_to_main.clicked.connect(lambda: self.stacked.setCurrentWidget(self.window.startpage))
        self.window.tc_to_single.clicked.connect(self.show_toolB_page)

