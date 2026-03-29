from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFrame, QHBoxLayout
from PySide6.QtWidgets import QPushButton, QSizePolicy, QTextBrowser, QVBoxLayout, QWidget
from PySide6.QtCore import QSettings, QUrl, Qt

from ampullary_ui.info import DOCS_ROOT_FILE

class HelpDialog(QDialog):

    def __init__(self, parent=None) -> None:
        super().__init__(parent=parent)
        self._settings = QSettings()
        width = int(self._settings.value("help/width", 640))
        height = int(self._settings.value("help/height", 480))
        x = int(self._settings.value("help/pos_x", 100))
        y = int(self._settings.value("help/pos_y", 100))

        self.setModal(True)
        self.setMinimumSize(640, 480)
        self.resize(width, height)
        self.move(x, y)
        self.finished.connect(self.on_finished)
        self.help = HelpBrowser()

        self.help._edit.historyChanged.connect(self._on_history_changed)

        self.back_btn = QPushButton(QIcon(":/icons/back"), "back")
        self.back_btn.setEnabled(False)
        self.back_btn.clicked.connect(self.help._edit.backward)
        self.home_btn = QPushButton(QIcon(":/icons/home"), "home")
        self.home_btn.clicked.connect(self.help._edit.home)
        self.fwd_btn = QPushButton(QIcon(":/icons/fwd"), "forward")
        self.fwd_btn.setLayoutDirection(Qt.RightToLeft)
        self.fwd_btn.setEnabled(False)
        self.fwd_btn.clicked.connect(self.help._edit.forward)

        empty = QWidget()
        empty.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        hbox = QHBoxLayout()
        hbox.addWidget(self.back_btn)
        hbox.addWidget(self.home_btn)
        hbox.addWidget(self.fwd_btn)
        hbox.addWidget(empty)

        bbox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        bbox.accepted.connect(self.accept)
        layout = QVBoxLayout()

        layout.addLayout(hbox)
        layout.addWidget(self.help)
        layout.addWidget(bbox)
        self.setLayout(layout)

    def _on_history_changed(self):
        self.back_btn.setEnabled(self.help._edit.isBackwardAvailable())
        self.fwd_btn.setEnabled(self.help._edit.isForwardAvailable())

    def on_finished(self):
        self._settings.setValue("help/width", self.width())
        self._settings.setValue("help/height", self.height())
        self._settings.setValue("help/pos_x", self.x())
        self._settings.setValue("help/pos_y", self.y())


class HelpBrowser(QWidget):

    def __init__(self, parent=None) -> None:
        super().__init__(parent=parent)
        self.setLayout(QVBoxLayout())
        doc_url = QUrl.fromLocalFile(DOCS_ROOT_FILE)
        self._edit = QTextBrowser()
        self._edit.setOpenLinks(True)
        self._edit.setOpenExternalLinks(True)
        self._edit.setSource(doc_url)
        self._edit.setEnabled(True)
        self._edit.setFrameShape(QFrame.NoFrame)

        self.layout().addWidget(self._edit)
