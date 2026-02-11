from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout

class CancelConfirmDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cancel simulation?")
        self.setMinimumSize(400, 200)

        layout = QVBoxLayout(self)

        label = QLabel("Do you want to save the current results before cancelling?")
        label.setWordWrap(True)
        layout.addWidget(label)

        # Buttons in horizontal layout
        button_layout = QHBoxLayout()

        self.save_btn = QPushButton("Save and Cancel")
        self.discard_btn = QPushButton("Cancel without Saving")
        self.abort_btn = QPushButton("Keep Running")

        # Optionally increase button size
        for btn in (self.save_btn, self.discard_btn, self.abort_btn):
            btn.setMinimumHeight(26)
            btn.setMinimumWidth(130)

        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.discard_btn)
        button_layout.addWidget(self.abort_btn)

        layout.addLayout(button_layout)

        # Connect buttons to accept/reject or custom slots
        self.save_btn.clicked.connect(lambda: self.done(1))
        self.discard_btn.clicked.connect(lambda: self.done(2))
        self.abort_btn.clicked.connect(lambda: self.done(0))