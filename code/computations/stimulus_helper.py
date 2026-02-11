"""
Helper functions for using the Stimulus in brian2 simulation

- Convert stimulus artificially into Hz/%, use theoretical EOD from -1 to 1 mV/cm as reference
- Compute needed filler lengths to simplify working with constructed gwn simulation stimulus later on
- Modify Stimulus including baseline stimulation and gwn stimulation into TimedArray for brian2 LIF simulation
- Load gwn stimulus data and make stimmulus array for simulation as TimedArray
- Load gwn stimulus data and make stimulus array for simulation + stimulus length for convenience 

--> could probably all go except load stimulus, leave it for now since i might need if if i offer to build own stimulus?
"""
import os
import pickle
import json
import numpy as np
from brian2 import TimedArray
from computations.lif_simulation import defaultclock


def stimulus_scaling_artificial (stimulus_og, wanted_sd=0.2):
    """
    convert stimulus artificially into mV/cm, use theoretical EOD from -1 to 1 mV/cm as reference

    Parameters
    ----------
    stimulus_og : np.array(n,)
        stimulus size corresponding to each recorded time point, unit-less
    wanted_sd : float
        wanted standartdiviation in decimal, NOT IN PERCENTAGE, default is 0.2
    Returns
    -------
    stimulus : np.array(n,)
        stimulus size corresponding to each recorded time point, in mV/cm
    """
    stim_sd = 0.3 
    eod_amplitude = 2.0 # from -1 to 1
    scaling = (eod_amplitude*wanted_sd)/stim_sd
    stimulus = (stimulus_og * scaling)/eod_amplitude
    return stimulus


def filler_length_gwn(gwn_time, samplingrate):
    """
    Needed filler lengths to simplify working with constructed simulation stimulus later on. 

    For simulation baseline, gwn stim und step stim will be concatenated. Later the simulation output will be seperated into the three different stimulation parts. Since the gwn stimuli have uneven durations, there will be short pauses between them to make simulation easier. This function gives workable timelengths in s for making small start segments and stick them to the stimuli for a better length. 
    Having even lengths and the duration of those segments saved will be importent, otherwise seperating data for analysis will be very painful for my brain
    
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


def modify_stimulus(stim_data):
    """
    Modify Stimulus 

    Adds start segment of 0 stimulation for the adaptation time and repeats stimulus
    Add "BaselineActivity" segment of 0 Stimulation for simulating baseline activity
    Add end segment to stimulus to make it 10s exactly long 
    Repeat stimulus(+ endsegment) for a specific number of times
    used to: Converts the stimulus np.array to a TimedArray for Brian2 (function of time), but changed for joblib parallel, which doesn't take TimedArrays as arguments 

    Parameters
    ----------
    gwn_stim_data : dict
        dictionary including stimulus values (unitless) and time in seconds, samplingrate, timestep of recording/simulation, adaptation time before simulation,number of times the original stimulus was repeated in the simulation and the length of baseline recording/simulation before gwn stimulation starts.
    
    Return
    ------
    mod_stimulus : np.ndarray
        stimulus size corresponding to each time point, dt = default 50us

    """
    # adaption time 1s, baselineactivity 2s 
    samplingrate = stim_data['samplingrate']
    adaptation_time = stim_data['adaptation_time']
    baseline_recording = stim_data['baseline_recording']
    repetitions = stim_data['repetitions']
    stimulus = stim_data['stimulus']
    stimulus = stimulus_scaling_artificial(stimulus)
    time = stim_data['stim_time']
    filler = filler_length_gwn(time, samplingrate)
    start_segment = np.zeros(int(samplingrate*(adaptation_time + baseline_recording)))
    end_segment = np.zeros(int(filler*samplingrate)) # add 0.00095 s
    stim_10s = np.concatenate((stimulus, end_segment), axis=0)
    stim_elongated = np.tile(stim_10s, repetitions)
    mod_stimulus = np.concatenate((start_segment, stim_elongated), axis=0)
    #timed_stimulus = TimedArray(mod_stimulus, defaultclock.dt) 
    # --> needs to be done outside of the function, since I cannot give a TimedArray as argument to joblib parallel
    return mod_stimulus


def load_simulation_stimulus():
    """
    Load gwn stimulus data and make stimmulus array for simulation
    Converts the stimulus np.array to a TimedArray for Brian2 (function of time)
    Path for loading from acquiring.paths

    Parameters
    ----------
    None

    Returns
    -------
    gwn_stim_data : dict
        GWN Stimulus used for training, dictionary includes stimulus itself, as well as meta data and time array
    timed_stimulus : TimedArray
        stimulus size corresponding to each time point, unit-less as a function of time    
    """
    filepath = os.path.join("..", "stimuli", "simstimrep_gwn150Hz10s0.3.npy")
    with open(filepath, 'rb') as handle:
        gwn_stim_data = pickle.load(handle)
    stimulus = modify_stimulus(gwn_stim_data)
    timed_stimulus = TimedArray(stimulus, defaultclock.dt) 
    return gwn_stim_data, timed_stimulus


def get_stimulus_and_data():
    """
    Load gwn stimulus data and make stimulus array for simulation
    Also load the stimulus length here for convenience 

    Parameters
    ----------
    None

    Returns
    -------
    stimulus : np.array
        stimulus size corresponding to each time point, dt = default 50us
    stim_data : dict
        GWN Stimulus used for training, dictionary includes stimulus itself, as well as meta data and time array
    stimulus_length : float
        stimulus length in seconds    
    """
    filepath = os.path.join("..", "stimuli", "simstimrep_gwn150Hz10s0.3.npy")
    with open(filepath, 'rb') as handle:
        stim_data = pickle.load(handle)
    stimulus = modify_stimulus(stim_data)
    filepath = os.path.join("general_helpers", "common_variables.json")
    with open(filepath, "r") as file:
        common_variables = json.load(file)
    return stimulus, stim_data, common_variables['stimulus_length']