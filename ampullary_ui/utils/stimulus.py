import numpy as np

from PySide6.QtCore import QFile, QIODevice


def scale_stimulus(stimulus_og, og_sd, wanted_sd=0.2):
    """
    scale stimulus to have the desired standard deviation

    Parameters
    ----------
    stimulus_og : np.array(n,)
        stimulus size corresponding to each recorded time point, unit-less
    wanted_sd : float
        wanted standard deviation in decimal, NOT IN PERCENTAGE, default is 0.2
    Returns
    -------
    stimulus : np.array(n,)
        stimulus size corresponding to each recorded time point, in mV/cm
    """
    scaling = wanted_sd / og_sd
    scaled_stimulus = stimulus_og * scaling
    return scaled_stimulus


def filler_length_gwn(gwn_time, samplingrate):
    """
    Needed filler lengths to simplify working with constructed simulation stimulus later on. 

    For the simulations, baseline period amd white noise period will be concatenated. Later, the simulation output will be split into the two respective parts. Since the gwn stimuli have uneven durations, there will be short pauses between them to make simulation easier. This function gives workable timelengths in s for making small start segments and stick them to the stimuli for a better length. 
    Having even lengths and the duration of those segments saved will be important, otherwise separating data for analysis will be very painful for my brain
    
    Parameters
    ----------
    gwn_time : ndarray
        time array of gwn stimulus
    sampligrate : float
        sampligrate
    
    Return
    ------
    gwn_filler : float
        length of add on segment in s    
    """
    gwn_filler = np.round(10.0 - gwn_time[-1] - 1/samplingrate, 9)
    return gwn_filler


def modify_stimulus(stim_data, baseline_duration=30., base_extratime=1.0,
                    trials=10, desired_stimsd=0.2):
    """
    Modify Stimulus 

    Adds start segment of 0 stimulation for the adaptation time and repeats stimulus
    Add "BaselineActivity" segment of 0 Stimulation for simulating baseline activity
    Add end segment to stimulus to make it 10s exactly long 
    Repeat stimulus(+ endsegment) for a specific number of times
    used to: Converts the stimulus np.array to a TimedArray for Brian2 (function of time),
    but changed for joblib parallel, which doesn't take TimedArrays as arguments 

    Parameters
    ----------
    gwn_stim_data : dict
        dictionary including stimulus values (unitless) and time in seconds, samplingrate,
        timestep of recording/simulation, adaptation time before simulation,number of times
        the original stimulus was repeated in the simulation and the length of baseline 
        recording/simulation before gwn stimulation starts.

    Return
    ------
    mod_stimulus : np.ndarray
        stimulus size corresponding to each time point, dt = default 50us
    """
    samplingrate       = stim_data['samplingrate']
    stimulus           = stim_data['stimulus']

    stimulus = scale_stimulus(stimulus, stim_data["sd"], desired_stimsd)
    baseline_segment = np.zeros(int(samplingrate * (base_extratime + baseline_duration)))
    stim_repeated = np.tile(stimulus, trials)
    mod_stimulus = np.concatenate((baseline_segment, stim_repeated), axis=0)

    return mod_stimulus


def load_gwnstimulus(dt: float = 1./20_000.):
    """
    Load gwn stimulus data  

    Parameters
    ----------
    dt : float
        The desired time step of the stimulus. Defaults to 1/20000

    Returns
    -------
    gwn_stim_data : dict
        GWN Stimulus dictionary that includes stimulus and stimulus metadata
    """
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

    def _finditem(obj: dict, key: any):
        if key in obj: return obj[key]
        for k, v in obj.items():
            if isinstance(v,dict):
                item = _finditem(v, key)
                if item is not None:
                    return item

    f = QFile(":/stimuli/gwn150Hz10s0.3.dat")
    if not f.open(QIODevice.ReadOnly):
        raise FileNotFoundError(f.name())
    lines = f.readAll().data().decode("utf-8").split("\n")
    f.close()
    lines = [l.lstrip().rstrip() for l in lines]
    s = _parse_stim_lines(lines)
    dur = _finditem(s[0], "T")
    dur = float(dur[:-1])
    sd  = _finditem(s[0], "sd")
    sd = float(sd)
    fc  = _finditem(s[0], "fc")
    fc = float(fc[:-2])
    time = s[0]['data'][:, 0]
    ampl = s[0]["data"][:,1]

    time_new = np.linspace(0.0, dur, int(dur / dt))
    ampl_new = np.interp(time_new, time, ampl)
    ampl_new[ampl_new > time[-1]] = ampl[-1]

    stim_data = {"name" : f.fileName().split("/")[-1].split(".dat")[0],
                 "samplingrate" : np.round(1 / dt),
                 "duration" : dur,
                 "dt" : dt,
                 "sd" : sd,
                 'fcutoff' : fc,
                 'stimulus' : ampl_new,
                 'stim_time' : time_new,
                }

    return stim_data
