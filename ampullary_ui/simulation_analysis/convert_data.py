"""
Functions for converting simulated data into format/structure with witch I can use the same analysis functions and structure as 
with the recorded data:

- Seperate simulated data of baseline activity from simulated data during stimulation with gwn
- Seperate simulated data of baseline activity from simulated data during stimulation with gwn, including membrane voltage
- Compute spike times relative to stimulus start for all repetitions of the stimulation
"""


import numpy as np
from brian2.units.allunits import second
from ampullary_ui.computations.lif_simulation import defaultclock



# def seperate_data(data, baseline_recording):
#     """
#     Seperate simulation data

#     Seperate simulated data of baseline activity from simulated data during stimulation with gwn
#     - Simulation time
#     - spikes 
#     and make spike lists out of timepoints and neuron indices

#     Parameter
#     ----------
#     data : dictionary 
#         dictionary with spike_idx, spike_times and time
#     baseline_recording : float 
#         time length for simulating baseline activity in seconds

#     Returns
#     -------
#     baseline : dictionary 
#         dictionary with spikes and time only during simulation without stimulation
#     stimulation : dictionary 
#         dictionary with spikes,and time only during simulation with gwn stimulation

#     """
#     n_neurons = data['n_neurons']
#     time = np.round(data['time'], 9)
#     switch_time = baseline_recording*1000
#     switch_ind = int(baseline_recording*second/defaultclock.dt)
#     time_baseline = time[:switch_ind]
#     time_stimulation = time[switch_ind:]
#     spikes_baseline = [[] for _ in range(n_neurons)]
#     spikes_stimulation = [[] for _ in range(n_neurons)]
#     for i in range(n_neurons):
#         spikes_baseline[i] = data["spike_times"][(data["spike_idx"] == i) & (
#             data["spike_times"] < switch_time)] / 1000
#         # spikes_baseline[i] = (data['spike_times'])[np.where(((data['spike_idx']) == i) & ((data['spike_times']) < switch_time))[0]] /1000
#         # spikes_stimulation[i] = (data['spike_times'])[np.where(((data['spike_idx']) == i) & ((data['spike_times']) > switch_time))[0]]  /1000
#         spikes_stimulation[i] = data["spike_times"][(data["spike_idx"] == 1) & (
#             data["spike_times"] < switch_time)] / 1000
#     baseline = dict(
#         time=time_baseline/1000,
#         spikes=spikes_baseline)
#     stimulation = dict(
#         time=time_stimulation/1000,
#         spikes=spikes_stimulation)
#     return baseline, stimulation


# def split_data(data, baseline_duration, stimulus_trialduration=10.0):
#     """
#     Seperate simulation data ! including membrane voltage

#     Seperate simulated data of baseline activity from simulated data during stimulation with gwn
#     - Simulation time
#     - membrane voltage
#     - spikes 
#     and make spike lists out of timepoints and neuron indices

#     Parameter
#     ----------
#     data : dictionary 
#         dictionary with spike_idx, spike_times, time and membrane_voltage
#     baseline_recording : float 
#         time length for simulating baseline activity in seconds

#     Returns
#     -------
#     baseline : dictionary 
#         dictionary with spikes, time and membrane_voltage only during simulation without stimulation
#     stimulation : dictionary 
#         dictionary with spikes, time and membrane_voltage only during simulation with gwn stimulation

#     """
#     n_neurons = data['n_neurons']
#     time = np.round(data['time'], 9)
#     switch_time_ms = baseline_duration*1000
#     switch_ind = int(baseline_duration*second / defaultclock.dt)

#     time_baseline = time[:switch_ind]
#     time_stimulation = time[switch_ind:] - switch_time_ms

#     mvoltage_baseline = None
#     mvoltage_stimulation = None

#     if "membrane_voltage" in data:
#         mvoltage_baseline = np.zeros((n_neurons, switch_ind))
#         mvoltage_stimulation = np.zeros((n_neurons, len(time) - switch_ind))
#         for i in range(n_neurons):
#             mvoltage_baseline[i, :] = data['membrane_voltage'][i][:switch_ind]
#             mvoltage_stimulation[i, :] = data['membrane_voltage'][i][switch_ind:]

#     spikes_baseline = [[] for _ in range(n_neurons)]
#     spikes_stimulation = [[] for _ in range(n_neurons)]
#     for i in range(n_neurons):
#         spikes_baseline[i] = data["spike_times"][(data["spike_idx"] == i) & (data["spike_times"] < switch_time_ms)] / 1000
#         temp = data["spike_times"][(data["spike_idx"] == i) & (data["spike_times"] >= switch_time_ms)]
#         spikes_stimulation[i] = (temp - switch_time_ms) / 1000

#     baseline = dict(time=time_baseline/1000, membrane_voltage=mvoltage_baseline, spikes=spikes_baseline)
#     stimulation = dict(time=time_stimulation/1000, membrane_voltage=mvoltage_stimulation, spikes=spikes_stimulation,
#                        trial_duration=stimulus_trialduration)

#     return baseline, stimulation


