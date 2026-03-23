import json
import ampullary_ui.resources_rc

from PySide6.QtCore import QFile, QIODevice, QTextStream

def load_json(resource):
    f = QFile(resource)
    if not f.open(QIODevice.ReadOnly | QIODevice.Text):
        raise FileNotFoundError(resource)
    common_variables = json.loads(bytes(f.readAll()).decode("utf-8"))
    return common_variables

def load_common_variables():
    res = ":/configs/common_variables"
    return load_json(res)

def load_labels():
    res = ":/configs/labels"
    return load_json(res)

def load_style():
    style_file = QFile(":/configs/style")
    style_file.open(QFile.ReadOnly | QFile.Text)
    stream = QTextStream(style_file)
    style = stream.readAll()
    style_file.close()
    return style

def load_stimuli(stim):
    pass