import sys

from PySide6.QtWidgets import QApplication

import ampullary_ui.resources_rc
from ampullary_ui.controllers.main_controller import MainController
from ampullary_ui.controllers.ui_loding_helper import load_ui
from ampullary_ui.utils import load_style


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    # style_file = QFile(":/configs/style")
    # style_file.open(QFile.ReadOnly | QFile.Text)
    # stream = QTextStream(style_file)
    # style = stream.readAll()
    # style_file.close()
    style = load_style()
    app.setStyleSheet(style)
    window = load_ui(":/ui/gui")
    controller = MainController(window)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

"""   
Questions for Jan to tool:

- setup placeholder, show figure, → should I share methods, and if so, how?
- how to handle explanation, info page? More useful figures? Just paper ref? pillte pictorgams include?
- do I need to somehow incorporate table convert or is line in terminal fine? (finish first)
- do we have a windows laptop around to try this out?
- can I ask the other people for feedback / finding bugs?
- labeling: B1 B2 ETC include or not (currently inconsistent)
- something I noted on the TEX
"""