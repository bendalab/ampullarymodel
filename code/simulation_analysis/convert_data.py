"""
Functions for converting simulated data into format/structure with witch I can use the same analysis functions and structure as 
with the recorded data:

- Seperate simulated data of baseline activity from simulated data during stimulation with gwn
- Seperate simulated data of baseline activity from simulated data during stimulation with gwn, including membrane voltage
- Compute spike times relative to stimulus start for all repetitions of the stimulation
"""


import numpy as np
from brian2.units.allunits import second
from computations.lif_simulation import defaultclock


def seperate_data(data, baseline_recording):
    """
    Seperate simulation data

    Seperate simulated data of baseline activity from simulated data during stimulation with gwn
    - Simulation time
    - spikes 
    and make spike lists out of timepoints and neuron indices

    Parameter
    ----------
    data : dictionary 
        dictionary with spike_idx, spike_times and time
    baseline_recording : float 
        time length for simulating baseline activity in seconds

    Returns
    -------
    baseline : dictionary 
        dictionary with spikes and time only during simulation without stimulation
    stimulation : dictionary 
        dictionary with spikes,and time only during simulation with gwn stimulation

    """
    n_neurons = data['n_neurons']
    time = np.round(data['time'], 9)
    switch_time = baseline_recording*1000
    switch_ind = int(baseline_recording*second/defaultclock.dt)
    time_baseline = time[:switch_ind]
    time_stimulation = time[switch_ind:]
    spikes_baseline = [ [] for _ in range(n_neurons) ]
    spikes_stimulation = [ [] for _ in range(n_neurons) ]
    for i in range(n_neurons):
        spikes_baseline[i] = (data['spike_times'])[np.where(((data['spike_idx']) == i) & ((data['spike_times']) < switch_time))[0]] /1000
        spikes_stimulation[i] = (data['spike_times'])[np.where(((data['spike_idx']) == i) & ((data['spike_times']) > switch_time))[0]]  /1000
    baseline = dict(
        time = time_baseline/1000,
        spikes = spikes_baseline)
    stimulation = dict(
        time = time_stimulation/1000,
        spikes = spikes_stimulation)
    return baseline, stimulation


def seperate_data_incl_membvol(data, baseline_recording):
    """
    Seperate simulation data ! including membrane voltage

    Seperate simulated data of baseline activity from simulated data during stimulation with gwn
    - Simulation time
    - membrane voltage
    - spikes 
    and make spike lists out of timepoints and neuron indices

    Parameter
    ----------
    data : dictionary 
        dictionary with spike_idx, spike_times, time and membrane_voltage
    baseline_recording : float 
        time length for simulating baseline activity in seconds

    Returns
    -------
    baseline : dictionary 
        dictionary with spikes, time and membrane_voltage only during simulation without stimulation
    stimulation : dictionary 
        dictionary with spikes, time and membrane_voltage only during simulation with gwn stimulation

    """
    n_neurons = data['n_neurons']
    time = np.round(data['time'], 9)
    switch_time = baseline_recording*1000
    switch_ind = int(baseline_recording*second/defaultclock.dt)
    time_baseline = time[:switch_ind]
    time_stimulation = time[switch_ind:]
    mvoltage_baseline = [ [] for _ in range(n_neurons) ]
    mvoltage_stimulation = [ [] for _ in range(n_neurons) ]
    for i in range(n_neurons):
        mvoltage_baseline[i] = data['membrane_voltage'][i][:switch_ind]
        mvoltage_stimulation[i] = data['membrane_voltage'][i][switch_ind:]
    spikes_baseline = [ [] for _ in range(n_neurons) ]
    spikes_stimulation = [ [] for _ in range(n_neurons) ]
    for i in range(n_neurons):
        spikes_baseline[i] = (data['spike_times'])[np.where(((data['spike_idx']) == i) & ((data['spike_times']) < switch_time))[0]] /1000
        spikes_stimulation[i] = (data['spike_times'])[np.where(((data['spike_idx']) == i) & ((data['spike_times']) > switch_time))[0]]  /1000
    baseline = dict(
        time = time_baseline/1000,
        membrane_voltage = mvoltage_baseline,
        spikes = spikes_baseline)
    stimulation = dict(
        time = time_stimulation/1000,
        membrane_voltage = mvoltage_stimulation, 
        spikes = spikes_stimulation)
    return baseline, stimulation


def relativ_stimulation_times(stimulation, baseline_recording):
    """
    Compute relative gwn stimulation spike times

    Cut whole stimulation time (10x stimulation) into snippets starting with the beginn of the 9.9995s stimulus and ending with the stimulation. 
    Cutting the spike array accordingly and changing the spike times from absolut time within the simulation to time relative to stimulus start.
    -> data['spikes'][x] = list of arrays, can use same conv_rate function, sta_function etc as in the recording analysis
    
    ATTENTION: 'end snippet length hardcoded here, find way to get info from modify_stimulus to here? Or doesn't matter because I won't change this?
                does not include membrane voltage since I don't need it for further analysis, only for plotting baseline comparison figure

    Parameters
    ----------
    stimulation : dictionary 
        dictionary with spikes and time only during simulation with gwn stimulation, optional: membrane voltage
    baseline_recording : float 
        time length for simulating baseline activity in seconds 

    Returns
    -------
    data : dict
        dictionary with stimulation time for one repetition of the stimulus (9.9995s) and the relative spike times within the repeated stimulation
    """
    end_snippet = 0.00095
    cut_idx = 19
    n_neurons = len(stimulation['spikes'])
    time = stimulation['time']
    start_times = np.unique(np.round(time, -1)) # + baseline_recording # neet not with 30 but with 2s sim
    start_times = np.delete(start_times, -1)  # left in for looping through, so I dont need endtime arrays
    stop_times = start_times + 10.0
    n_stims = len(start_times)
    start_idxs = np.zeros(n_stims)
    for i in range(n_stims):
        start_idxs[i] = np.where(time==start_times[i])[0]
    start_idxs = start_idxs.astype(int)
    rel_stim_time = time[start_idxs[0]:start_idxs[1]-cut_idx] - baseline_recording
    rel_spikes = [ [] for _ in range(n_neurons) ]
    for j in range(n_neurons):
        single_stimulations = [ [] for _ in range(n_stims) ]
        for i in range(n_stims):
            single_stimulations[i] = stimulation['spikes'][j][np.where((stimulation['spikes'][j] >= start_times[i]) & (stimulation['spikes'][j] < stop_times[i]-end_snippet))[0]]   
        for k in range(len(single_stimulations)):
            single_stimulations[k] -= k*10.0 + baseline_recording
        rel_spikes[j] = single_stimulations
    data = {
        'time' : rel_stim_time, 
        'spikes' : rel_spikes}
    return data

