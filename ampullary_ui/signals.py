from PySide6.QtCore import Signal, QObject

class DataReaderSignals(QObject):
    finished = Signal(bool)
    error = Signal(str)
    progress = Signal(str, float)
