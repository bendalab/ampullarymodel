from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PySide6.QtCore import QSize

class AspectRatioFigureCanvas(FigureCanvas):
    def __init__(self, fig, aspect_ratio):
        super().__init__(fig)
        self.aspect_ratio = aspect_ratio  # width / height

    def sizeHint(self):
        width = super().sizeHint().width()
        height = int(width / self.aspect_ratio)
        return QSize(width, height)

    def resizeEvent(self, event):
        w = event.size().width()
        h = int(w / self.aspect_ratio)
        self.resize(w, h)
        super().resizeEvent(event)
