import json
import numpy as np
import ampullary_ui.resources_rc

from brian2.units import usecond
from PySide6.QtCore import QFile, QIODevice, QTextStream, QFileInfo


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


def _parse_stim_lines(lines):
    ret = []
    dat = {}
    X = []
    keyon = False
    currkey = None
    for l in lines:
        # if empty line and we have data recorded
        if (not l or l.startswith('#')) and len(X) > 0:
            keyon = False
            currkey = None
            dat['data'] = np.array(X)
            ret.append(dat)
            X = []
            dat = {}

        if '---' in l:
            continue
        if l.startswith('#'):
            if ":" in l:
                tmp = [e.rstrip().lstrip() for e in l[1:].split(':')]
                if currkey is None:
                    dat[tmp[0]] = tmp[1]
                else:
                    dat[currkey][tmp[0]] = tmp[1]
            elif "=" in l:
                tmp = [e.rstrip().lstrip() for e in l[1:].split('=')]
                if currkey is None:
                    dat[tmp[0]] = tmp[1]
                else:
                    dat[currkey][tmp[0]] = tmp[1]
            elif l[1:].lower().startswith('key'):
                dat['key'] = []
                keyon = True
            elif keyon:
                dat['key'].append(tuple([e.lstrip().rstrip() for e in l[1:].split()]))
            else:
                currkey = l[1:].rstrip().lstrip()
                dat[currkey] = {}

        elif l:  # if l != ''
            keyon = False
            currkey = None
            X.append([float(e) for e in l.split()])

    if len(X) > 0:
        dat['data'] = np.array(X)
    else:
        dat['data'] = []
    ret.append(dat)

    return tuple(ret)


def load_gwn_stimulus(stim_duration=10, dt=1./20_000.):
    f = QFile(":/stimuli/gwn150Hz10s0.3.dat")
    if not f.open(QIODevice.ReadOnly):
        raise FileNotFoundError(f.name())
    lines = f.readAll().data().decode("utf-8").split("\n")
    f.close()
    lines = [l.lstrip().rstrip() for l in lines]
    s = _parse_stim_lines(lines)
    x_org = s[0]['data'][:, 0]
    y_org = s[0]["data"][:,1]
    x_new = np.linspace(0.0, stim_duration, int(stim_duration / dt))
    y_new = np.interp(x_new, x_org, y_org)
    x_new[x_new > x_org[-1]] = x_org[-1]

    data = {"name" : f.fileName().split("/")[-1].split(".dat")[0],
            "samplingrate" : np.round(1 / dt),
            "dt" : dt * 1000000 * usecond,
            'adaptation_time': 1.0,
            'baseline_recording': 30.0,
            'repetitions': 10,
            'stimulus': y_new,
            'stim_time' : x_new}

    return data


if __name__ == "__main__":
    d = load_gwn_stimulus()
    pass