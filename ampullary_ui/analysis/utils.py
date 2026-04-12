import numpy as np
from scipy.stats import norm


def unwrap_spiketrains(spike_times, spike_ids):
    """
    Separate spike times into individual spike trains based on unit IDs.
    This function takes arrays of spike times and corresponding unit identifiers,
    and groups spike times by their unit ID, returning a list of spike trains
    where each element corresponds to all spike times for a particular unit.
    Parameters
    ----------
    spike_times : np.ndarray
        Array of spike times (timestamps) for all spikes.
    spike_ids : np.ndarray
        Array of unit IDs corresponding to each spike time.
        Must have the same length as spike_times.
    Returns
    -------
    list of np.ndarray
        List of spike time arrays, one for each unique unit ID.
        Each array contains all spike times for that unit, sorted by ID order.
    Examples
    --------
    >>> spike_times = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
    >>> spike_ids = np.array([1, 2, 1, 2, 1])
    >>> trains = unwrap_spiketrains(spike_times, spike_ids)
    >>> trains[0]  # Unit 1
    array([0.1, 0.3, 0.5])
    >>> trains[1]  # Unit 2
    array([0.2, 0.4])
    """
    unique_ids = np.unique(spike_ids)
    spike_trains = []
    for id in unique_ids:
        spike_trains.append(spike_times[spike_ids == id])

    return spike_trains


def split_data(simulation_data, baseline_duration,
               stimulus_duration=10.0):
    """
    Split simulation data into baseline and stimulus-driven data.

    Parameter
    ----------
    data : dictionary 
        dictionary with spike_idx, spike_times, time, dt, and membrane_voltage
    baseline_recording : float 
        time length for simulating baseline activity in seconds
    stimulus_duration: float
        the duration of a single stimulus driven trial in seconds.
    Returns
    -------
    baseline : dictionary 
        dictionary with spikes, time and membrane_voltage only during simulation without stimulation
    stimulation : dictionary 
        dictionary with spikes, time and membrane_voltage only during simulation with gwn stimulation

    """
    n_neurons = simulation_data['n_neurons']
    dt = simulation_data["dt"]
    time = np.round(simulation_data['time'], 9)
    switch_time = baseline_duration
    switch_ind = int(baseline_duration / dt)

    time_baseline = time[:switch_ind]
    time_stimulation = time[switch_ind:] - switch_time

    mvoltage_baseline = None
    mvoltage_stimulation = None

    if "membrane_voltage" in simulation_data:
        mvoltage_baseline = np.zeros((n_neurons, switch_ind))
        mvoltage_stimulation = np.zeros((n_neurons, len(time) - switch_ind))
        for i in range(n_neurons):
            mvoltage_baseline[i, :] = simulation_data['membrane_voltage'][i][:switch_ind]
            mvoltage_stimulation[i, :] = simulation_data['membrane_voltage'][i][switch_ind:]

    spikes_baseline = [[] for _ in range(n_neurons)]
    spikes_stimulation = [[] for _ in range(n_neurons)]
    spike_trains = unwrap_spiketrains(simulation_data["spike_times"], simulation_data["spike_idx"])
    for i, spike_times in enumerate(spike_trains):
        spikes_baseline[i] = spike_times[spike_times < switch_time]
        spikes_stimulation[i] = spike_times[spike_times >= switch_time] - switch_time

    baseline = dict(time=time_baseline,
                    membrane_voltage=mvoltage_baseline,
                    spikes=spikes_baseline,
                    baseline_duration=baseline_duration, dt=dt)
    stimulation = dict(time=time_stimulation,
                       membrane_voltage=mvoltage_stimulation,
                       spikes=spikes_stimulation,
                       trial_duration=stimulus_duration,
                       dt=dt)

    return baseline, stimulation


def spiketimes_to_trials(noise_simulation_data):
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
    baseline_duration : float 
        time length for simulating baseline activity in seconds 

    Returns
    -------
    data : dict
        dictionary with stimulation time for one repetition of the stimulus (9.9995s) and the relative spike times within the repeated stimulation
    """
    n_neurons = len(noise_simulation_data['spikes'])
    time = noise_simulation_data['time']
    trial_duration = noise_simulation_data["trial_duration"]
    start_times= np.arange(0.0, time[-1], trial_duration)
    stop_times = start_times + trial_duration
    n_stims = len(start_times)
    has_membrane_voltage = "membrane_voltage" in noise_simulation_data
    has_membrane_voltage &= noise_simulation_data["membrane_voltage"] is not None
    spikes = [[] for _ in range(n_neurons)]
    voltages = [[] for _ in range(n_neurons)]
    
    trial_time = time[time < trial_duration]
    for j in range(n_neurons):
        stim_spikes = [[] for _ in range(n_stims)]
        stim_voltages = []

        neuron_spikes = noise_simulation_data['spikes'][j]
        neuron_voltage = None
        if has_membrane_voltage:
            neuron_voltage = noise_simulation_data["membrane_voltage"][j]
        for i,(start, stop) in enumerate(zip(start_times, stop_times)):
            spike_times = neuron_spikes[(neuron_spikes >= start) & (neuron_spikes < stop)]
            spike_times -= start
            stim_spikes[i] = spike_times
            if has_membrane_voltage:
                stim_voltages.append(neuron_voltage[(time >= start)& (time < stop)])

        spikes[j] = stim_spikes
        voltages[j] = np.array(stim_voltages) if has_membrane_voltage else None

    data = {'time': trial_time,
            'spikes': spikes,
            'membrane_voltages': voltages,
            'trial_duration': trial_duration,
            'dt': noise_simulation_data['dt']}
    return data


def convolution_rate(spike_times, time, sigma=0.0025, dt=1./20_000):
    """
    Firing rate computed by the convolution method.

    Makes a binary spike train with the length of the measured time out of the 
    spike times and uses a Gaussian Kernel for convolution.

    Parameters
    ----------
    spike_times : list of spikes times.
        Spike times for each trial in seconds. Note: when passing a single trial, wrap it in brackets e.g. [spike_times]
    time : np.array(n,)
        recording time in seconds 
    sigma : float, optional
        Standard deviation of the Gaussian kernels. The default is 0.0025.

    Returns
    -------
    conv_rate :  list or np.array(n,)
        Firing rate(s) corresponding to spikes in Hz. If spike_times is a list of trials, a list will be returned

    """
    conv_rates = np.zeros((len(spike_times), len(time)))
    for i in range(len(spike_times)):
        tmax = 4.0*sigma
        if 2.0*tmax > time[-1] - time[0]:
            tmax = 0.5*(time[-1] - time[0])
        ktime = np.arange(-tmax, tmax+dt, dt)
        kernel = norm.pdf(ktime, loc=0, scale=sigma)
        idx = np.asarray((spike_times[i]-time[0])/dt, dtype=int)
        binary_spikes = np.zeros(len(time))
        binary_spikes[idx[(idx >= 0) & (idx < len(time))]] = 1.0
        conv_rate_single = np.convolve(binary_spikes, kernel, mode="same")
        conv_rates[i, :] = conv_rate_single
    if len(spike_times) == 1:
        return conv_rates[0]
    
    return conv_rates


def convolution_rate_with_std(spike_times, time, sigma=0.0025):
    """
    Firing rate computed by the convolution method + STD.

    Makes a binary spike train with the length of the measured time out of the 
    spike times and uses a Gaussian Kernel for convolution. Also computes standard deviation

    Parameters
    ----------
    spike_times : np.arrays(k,)
        Spike times for each trial in seconds.
    time : np.array(n,)
        recording time in seconds 
    sigma : float, optional
        Standard deviation of the Gaussian kernels. The default is 0.0025.

    Returns
    -------
    conv_rate :  np.array(n,)
        Firing rate corresponding to spikes in Hz.
    std : np.array(n,)
        standard deviation
    """
    conv_rates = np.zeros((len(spike_times), len(time)))
    dt = np.round(time[1]-time[0], 7)
    for i in range(len(spike_times)):
        tmax = 4.0*sigma
        if 2.0*tmax > time[-1] - time[0]:
            tmax = 0.5*(time[-1] - time[0])
        ktime = np.arange(-tmax, tmax+dt, dt)
        kernel = norm.pdf(ktime, loc=0, scale=sigma)
        idx = np.asarray((spike_times[i]-time[0])/dt, dtype=int)
        binary_spikes = np.zeros(len(time))
        binary_spikes[idx[(idx >= 0) & (idx < len(time))]] = 1.0
        conv_rate_single = np.convolve(binary_spikes, kernel, mode="same")
        conv_rates[i, :] = conv_rate_single
    conv_rate = np.mean(conv_rates, axis=0)
    std = np.std(conv_rates, axis=0)
    return conv_rate, std


def convolution_rate_single(spike_times, time, sigma=0.0025):
    """
    Firing rate computed by the convolution method for a single trial.

    Makes a binary spike train with the length of the measured time out of the 
    spike times and uses a Gaussian Kernel for convolution.

    Parameters
    ----------
    spike_times : np.arrays(k,)
        Spike times for each trial in seconds.
    time : np.array(n,)
        recording time in seconds 
    sigma : float, optional
        Standard deviation of the Gaussian kernels. The default is 0.0025.

    Returns
    -------
    conv_rate :  np.array(n,)
        Firing rate corresponding to spikes in Hz, single trial

    """
    dt = np.round(time[1]-time[0], 7)
    tmax = 4.0*sigma
    if 2.0*tmax > time[-1] - time[0]:
        tmax = 0.5*(time[-1] - time[0])
    ktime = np.arange(-tmax, tmax+dt, dt)
    kernel = norm.pdf(ktime, loc=0, scale=sigma)
    idx = np.asarray((spike_times-time[0])/dt, dtype=int)
    binary_spikes = np.zeros(len(time))
    binary_spikes[idx[(idx >= 0) & (idx < len(time))]] = 1.0
    conv_rate = np.convolve(binary_spikes, kernel, mode="same")
    return conv_rate


def smoothing(data, span):
    """
    Smooth data

    Smooths data via convolution, with kernel span*2+1, replicates first and last entry to even out filter effect of smoothing

    Parameter
    ---------
    data : ndarray
        some data array
    span : int
        half the kernel size

    Returns
    -------
    data_convoluted : ndarray
        smoothed data array
    """
    kernel = np.ones(span*2 + 1) / (span*2 + 1)
    data_copy = data*1
    data_copy[0] = data_copy[1]
    start = np.array([data_copy[0]]*len(kernel))
    end = np.array([data_copy[-1]]*len(kernel))
    data_elongated = np.concatenate((start, data_copy, end), axis=0)
    data_convolved = np.convolve(data_elongated, kernel, mode='same')
    data_smoothed = np.split(data_convolved, [len(kernel), -len(kernel)])[1]
    return data_smoothed


def find_nearest(array, value):
    """
    finding the nearest value in an array to a given value

    Parameter
    ---------
    array : np.array
        array of interest
    value : float
        value of interst

    Return
    ------
    nearest value in an array to the given value
    """
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return array[idx]

