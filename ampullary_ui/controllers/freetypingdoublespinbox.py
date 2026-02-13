from PySide6.QtWidgets import QDoubleSpinBox
from PySide6.QtGui import QValidator

class FreeTypingDoubleSpinBox(QDoubleSpinBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def validate(self, input_str, pos):
        return (QValidator.Intermediate, input_str, pos)

    def fixup(self, input_str):
        try:
            val = float(input_str)
        except ValueError:
            val = self.minimum()
        if val < self.minimum():
            val = self.minimum()
        elif val > self.maximum():
            val = self.maximum()
        self.setValue(val)

