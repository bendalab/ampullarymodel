from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout, QWidget, QHBoxLayout
from PySide6.QtCore import Qt


class AboutDialog(QDialog):

    def __init__(self, parent=None) -> None:
        super().__init__(parent=parent)
        self.setModal(True)
        about = About(self)
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(about)
        bbox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        bbox.accepted.connect(self.accept)
        self.layout().addWidget(bbox)


class About(QWidget):

    def __init__(self, parent=None) -> None:
        super().__init__(parent=parent)
        self.setLayout(QVBoxLayout())
        self.layout().setAlignment(Qt.AlignHCenter)
        subheading = QLabel("Generate models of ampullary afferents.\n\nby Sarah Mayer & Jan Grewe\nNeuroethology\n University of Tübingen\nGermany")
        subheading.setAlignment(Qt.AlignCenter)
        font = subheading.font()
        font.setPointSize(14)
        font.setBold(True)

        link = QLabel("https://github.com/bendalab")
        link.setOpenExternalLinks(True)
        link.setAlignment(Qt.AlignCenter)

        iconlabel = QLabel()
        pixmap = QPixmap(":/icons/icon")
        s = pixmap.size()
        new_height = int(s.height() * 300/s.width())
        pixmap = pixmap.scaled(300, new_height, Qt.KeepAspectRatio, Qt.FastTransformation)
        iconlabel.setPixmap(pixmap)
        iconlabel.setAlignment(Qt.AlignCenter)
        iconlabel.setScaledContents(True)

        self.layout().addWidget(iconlabel)
        self.layout().addStretch()
        self.layout().addWidget(subheading)
        self.layout().addWidget(link)
