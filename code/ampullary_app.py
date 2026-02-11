import sys
import resources_rc 
from PySide6.QtWidgets import QApplication
from controllers.main_controller import MainController
from controllers.ui_loding_helper import load_ui


if __name__ == "__main__":

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    with open("style.qss", "r") as f:
        style = f.read()
    app.setStyleSheet(style)
    window = load_ui("gui_01.ui")
    controller = MainController(window)
    window.show()
    sys.exit(app.exec())

"""   
Questions for Jan to tool:

- setup placeholder, show figure, → should I share methode, and if so, how?
- how to handle explanation, info page? More usefull figures? Just paper ref? pillte pictorgams include?
- do I need to somehow incorperate table convert or is line in temrinal fine? (finish first)
- do we have a windows laptop around to try this out?
- can I ask the other people for feedback / finding bugs?
- labeling: B1 B2 ETC include or not (currently inconsistant)
- something I noted on the TEX
"""