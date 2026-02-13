from PySide6.QtCore import QFile
from PySide6.QtUiTools import QUiLoader
from controllers.freetypingdoublespinbox import FreeTypingDoubleSpinBox
from controllers.keepratiopixmaplabel import KeepRatioPixmapLabel

class UiLoader(QUiLoader):
    def createWidget(self, class_name, parent=None, name=""):
        if class_name == "FreeTypingDoubleSpinBox":
            widget = FreeTypingDoubleSpinBox(parent)
            widget.setObjectName(name)
            return widget
        if class_name == "KeepRatioPixmapLabel":
            widget = KeepRatioPixmapLabel(parent)
            widget.setObjectName(name)
            return widget
        return super().createWidget(class_name, parent, name)

def load_ui(path):
    loader = UiLoader()
    file = QFile(path)
    file.open(QFile.ReadOnly)
    window = loader.load(file)
    file.close()
    return window
