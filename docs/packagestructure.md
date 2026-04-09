# Ampullary-simulator package structure

There are three big parts, the first and second reside in the ampullary_ui package. The resources are in respective folders of the project's root folder

```
ampullary_simulator/
├─ ampullary_ui/
├─ docs/
├─ examples/
├─ source/
├─ stimuli/
├─ build-resources.py
├─ LICENSE
├─ Makefile
├─ pyproject.toml
├─ README.md
├─ requirements.txt
└─ setup.py
```

## The ``ampullary_ui`` package

```
ampullary_ui
├─ analysis/
├─ config/
├─ dialogs/
├─ gui/
├─ plotting/
├─ simulation/
├─ ui/
├─ utils/
├─ app.py
└─ resources.qrc
````

### The graphical user interface --- the UI

Graphical user interfaces are designed with the QT-Creator and stored as ``*.ui`` files.

#### UI specifications

The sub-packge ``ampullary_ui.ui`` contains the xml descriptors of the user interfaces. There should be ONE ``ui`` file for each custom widget. The start-page, for example, is specified by the ``startpage.ui`` xml file.

These need to be compiled into the respective python classes. This is done by calling:

```bash
> pyside6-uic startpage.ui -o startpage_ui.py
```

The ``build_resources.py`` script does that recursively for all ui files.

```bash
> python3 build_resources.py --ui
```

The resulting ``*_ui.py`` file is an ugly auto-generated python script that contains a single class, for example ``UI_StartPage`` 

The name of the class is read from the ui file, i.e. the top level widget's name

```xml
<class>StartPage</class>
 <widget class="QWidget" name="StartPage">
...
```

Interestingly the ``UI_StartPage`` class is **not** yet a QWidget that can be used directly. Rather, we need to write the actual code for the widget ourselves.

#### The actual QWidgets

reside in the ``ampullary_ui.gui`` subpackage. Continuing from above the actual ``StartPage`` class is created by the following piece of code

```python
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Signal, Qt

from ampullary_ui.ui import Ui_StartPage
from ampullary_ui.utils import Tool

class StartPage(QWidget):
    tool_selection = Signal(Tool)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.ui = Ui_StartPage()
        self.ui.setupUi(self)

        self._icon_width = 0.8 / 3
        self._icon_maxheight = 500
        self._pm1 = QPixmap(":/examples/eqn")
        self._pm2 = QPixmap(":/examples/get_model")
        self._pm3 = QPixmap(":/examples/table")
        for pixmap, label in zip([self._pm1, self._pm2, self._pm3],
                                 [self.ui.picture_1, self.ui.picture_2, self.ui.picture_3]):
            self._scaletofit(pixmap, label)

        self.resizeEvent = self._on_resize

        self.ui.simulatorbtn.clicked.connect(self._on_simulator)
        self.ui.generatorbtn.clicked.connect(self._on_generator)
        self.ui.catalogbtn.clicked.connect(self._on_catalog)
```

Important to note: We need to import the auto-generated ``Ui_StartPage`` from ``ampullary_ui.ui`` use it like ``self.ui = UiStartPage()`` and let the ui pull itself from the mud by calling ``self.ui.setupUI(self)``.

### The simulation and analysis

So far

## Resources and other data



