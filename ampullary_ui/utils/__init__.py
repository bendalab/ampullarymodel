import json

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

def load_new_order():
    res = ":/config/new_order"
    return load_json(res)

def load_style():
    style_file = QFile(":/configs/style")
    style_file.open(QFile.ReadOnly | QFile.Text)
    stream = QTextStream(style_file)
    style = stream.readAll()
    style_file.close()
    return style


from .saving import (
    ensure_folder,
    get_outputfolder,
    read_output_folder,
    save_data,
    save_features,
    save_features_table,
    save_figure,
    save_parameter_table,
    save_params,
    save_sampled_subset,
    store_output_folder,
)
from .stimulus import (
    filler_length_gwn,
    get_stimulus_and_data,
    load_gwnstimulus,
    modify_stimulus,
    scale_stimulus,
)

