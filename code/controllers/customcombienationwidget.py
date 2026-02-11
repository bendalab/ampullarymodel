import numpy as np
import matplotlib.pyplot as plt
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QDoubleSpinBox, QLabel
from PySide6.QtCore import Signal, QRect
from PySide6.QtGui import QPainter, QColor, QPen, Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from plotting.plot_helpers_general import plot_params
plt.rcParams.update(plot_params)



# ---------- Native RangeSlider ----------
class RangeSlider(QWidget):
    valueChanged = Signal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._min = 0
        self._max = 0
        self._low = 0
        self._high = 0
        self._scale = 1
        self._handle_radius = 8
        self._bar_height = 6
        self._active_handle = None
        self.setMinimumHeight(30)
        self.setMouseTracking(True)

    def setRange(self, minimum, maximum):
        self._min = minimum
        self._max = maximum
        self.update()

    def setValues(self, low: float, high: float):
        low_i = int(low * self._scale)
        high_i = int(high * self._scale)

        low_i = max(self._min, min(low_i, high_i))
        high_i = min(self._max, max(low_i, high_i))

        self._low, self._high = low_i, high_i
        self.valueChanged.emit(
            self._low / self._scale,
            self._high / self._scale
        )
        self.update()

    def setFloatRange(self, min_val, max_val, resolution=1000):
        self._scale = resolution
        self._min = int(min_val * resolution)
        self._max = int(max_val * resolution)
        self._low = self._min
        self._high = self._max
        self.update()

    def values(self):
        return self._low / self._scale, self._high / self._scale

    def _value_to_pos(self, value):
        w = self.width() - 2 * self._handle_radius
        return int(self._handle_radius + w * (value - self._min) / (self._max - self._min))

    def _pos_to_value(self, x):
        w = self.width() - 2 * self._handle_radius
        ratio = (x - self._handle_radius) / w
        return int(self._min + ratio * (self._max - self._min))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        center_y = self.height() // 2

        bar_rect = QRect(
            self._handle_radius,
            center_y - self._bar_height // 2,
            self.width() - 2 * self._handle_radius,
            self._bar_height,
        )
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#1d1d1d"))
        painter.drawRoundedRect(bar_rect, 3, 3)

        low_x = self._value_to_pos(self._low)
        high_x = self._value_to_pos(self._high)
        range_rect = QRect(low_x, bar_rect.top(), high_x - low_x, self._bar_height)
        painter.setBrush(QColor("#007ACC"))
        painter.drawRoundedRect(range_rect, 3, 3)

        handle_pen = QPen(QColor("#1d1d1d"))
        handle_pen.setWidth(1)
        painter.setPen(handle_pen)
        painter.setBrush(QColor("#444444"))
        painter.drawEllipse(low_x - self._handle_radius, center_y - self._handle_radius,
                            2 * self._handle_radius, 2 * self._handle_radius)
        painter.drawEllipse(high_x - self._handle_radius, center_y - self._handle_radius,
                            2 * self._handle_radius, 2 * self._handle_radius)

    def mousePressEvent(self, event):
        x = event.position().x()
        low_x = self._value_to_pos(self._low)
        high_x = self._value_to_pos(self._high)
        self._active_handle = "low" if abs(x - low_x) < abs(x - high_x) else "high"

    def mouseMoveEvent(self, event):
        if not self._active_handle:
            return
        value = self._pos_to_value(event.position().x())
        if self._active_handle == "low":
            self._low = max(self._min, min(value, self._high))
        else:
            self._high = min(self._max, max(value, self._low))
        self.valueChanged.emit( self._low / self._scale, self._high / self._scale)

        self.update()

    def mouseReleaseEvent(self, event):
        self._active_handle = None


class RangeCombine(QWidget):
    rangeChanged = Signal(float, float)
    finished = Signal()

    def __init__(self, data: np.ndarray, min_value: float, max_value: float, bin_specs: int | str, 
                 decimals = int, step = float, label: str | None = None, parent=None):
        super().__init__(parent)
        self.data = data
        self.min_value = min_value
        self.max_value = max_value
        self.bin_specs = bin_specs
        self.label = label

        # Matplotlib Figure
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumHeight(160)
        self.canvas.setMaximumHeight(200)
        
        # SpinBoxes
        self.min_box = QDoubleSpinBox()
        self.max_box = QDoubleSpinBox()
        self.min_box.setKeyboardTracking(False)
        self.max_box.setKeyboardTracking(False)
        # Spin boxes config
        for box in (self.min_box, self.max_box):
            box.setRange(self.min_value, self.max_value)
            box.setDecimals(decimals)
            box.setSingleStep(step)
            box.setAccelerated(True)
        # Initial values
        self.min_box.setValue(self.min_value)
        self.max_box.setValue(self.max_value)

        # Slider
        self.slider = RangeSlider()
        self.slider.setFloatRange(self.min_value, self.max_value, resolution=1000)
        self.slider.setValues(self.min_value, self.max_value)
        self.slider.setValues(self.min_value, self.max_value)

        # Layouts
        range_layout = QHBoxLayout()
        range_layout.addWidget(QLabel("Min"))
        range_layout.addWidget(self.min_box)
        range_layout.addWidget(self.slider, stretch=1)
        range_layout.addWidget(QLabel("Max"))
        range_layout.addWidget(self.max_box)
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.canvas)      # Figure above slider
        main_layout.addLayout(range_layout)
        self.setLayout(main_layout)

        # Connections
        self.slider.valueChanged.connect(self.on_slider_changed)
        self.min_box.valueChanged.connect(self.on_spinbox_live_change)
        self.max_box.valueChanged.connect(self.on_spinbox_live_change)
        self.min_box.editingFinished.connect(self.on_spinbox_editing_finished)
        self.max_box.editingFinished.connect(self.on_spinbox_editing_finished)


    # Sync logic
    def on_slider_changed(self, low, high):
        self.min_box.blockSignals(True)
        self.max_box.blockSignals(True)
        if self.min_box.value() != low:
            self.min_box.setValue(low)
        if self.max_box.value() != high:
            self.max_box.setValue(high)
        self.min_box.blockSignals(False)
        self.max_box.blockSignals(False)

    def on_spinbox_live_change(self):
        low = self.min_box.value()
        high = self.max_box.value()
        self.slider.setValues(low, high)
    
    def on_spinbox_editing_finished(self):
        low = self.min_box.value()
        high = self.max_box.value()
        if low > high:
            self.max_box.setValue(low)
            high = low
        self.slider.setValues(low, high)

    # current range!
    def current_range(self):
        return self.min_box.value(), self.max_box.value()
    
    # make histogram
    def make_histogram(self, hist):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        bins = hist["bins"]
        full = hist["full"]
        reduced = hist["reduced"]
        ax.bar(bins[:-1], full, width=np.diff(bins), color="#888", alpha=1.0, align="edge")
        ax.set_title(self.label, color="#44F9BD", pad=4, fontweight='bold')
        ax.get_yaxis().set_visible(False)
        ax.spines.left.set_visible(False)
        if reduced is not None:
            ax2 = ax.twinx()
            ax2.bar(bins[:-1], reduced, width=np.diff(bins), color="#44F9BD", alpha=0.6, align="edge")
            ax2.get_yaxis().set_visible(False)
            ax2.spines.left.set_visible(False)
        ax.figure.subplots_adjust(top=0.85, bottom=0.18)
        self.canvas.draw_idle()
        self.finished.emit()



    