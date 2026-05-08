import numpy as np
import pandas as pd

def serial_correlations(spikes, max_lag=10):
    """ Serial correlations of interspike intervals.

    Parameters
    ----------
    spikes: nparray of floats
        Spike times of baseline activity.
    max_lag: int
        Compute serial correlations up to this lag.

    Returns
    -------
    lags: ndarray of ints
        Lags for which interspike interval correlations have been computed.
        First one is zero, last one is `max_lag`.
    corrs: ndarray of floats
        Serial correlations for all `lags`.
    """
    intervals = np.diff(spikes)
    # intervals = intervals[~is_outlier(intervals)]
    lags = np.arange(0, max_lag + 1, 1)
    corrs = np.zeros(max_lag + 1)
    corrs[0] = np.corrcoef(intervals, intervals)[0, 1]
    for i, lag in enumerate(lags[1:]):
        corrs[i+1] = np.corrcoef(intervals[:-lag], intervals[lag:])[0, 1]
    return lags, corrs


def baseline_features(spike_trains, time):
    """
    Extract baseline features

    Computes firing rate, ISI CV and first lag correlation for every spike train in the data 

    Parameters 
    ----------
    spike_trains : list
    list of np.arrays that contain the spike times of each trial/cell. Times are given in seconds.
    time : np.array
    The time vector of the simulation. Given in seconds.

    Return
    ------
    frates : np.array
        mean firing rate of every simulated cell
    isi_cv : np.array
        Interstimulusintervall CV of every simulated cell
    corrs_arr : np.array
        first lag correlation of every simulated cell

    """
    counts = np.asarray([len(i) for i in spike_trains])
    frates = counts/np.round(time[-1] - time[0])
    isis = [np.diff(spike_times) for spike_times in spike_trains]
    isi_cvs = [np.std(i)/np.mean(i) for i in isis]
    isi_cvs = np.array(isi_cvs)
    n_neurons = len(spike_trains)
    corrs_arr = np.zeros(n_neurons)
    for i in range(n_neurons):
        _, corrs = serial_correlations(spike_trains[i], max_lag=10)
        corrs_arr[i] = corrs[1]
    temp = {"base_fr": frates, "isi_cv": isi_cvs,
            "serial_corr": corrs_arr}
    return temp

def baseline_plot_data(baseline_data, index=0):
    n_neurons = len(baseline_data["spikes"])
    if index < -n_neurons or  index > n_neurons - 1:
        raise ValueError("analysis.baseline.baseline_plot_data; invalid index!")
    lags, corrs = serial_correlations(baseline_data["spikes"][index], max_lag=10)

    ba = {
        'membrane_time' : [baseline_data['time']],
        'membrane_voltage' : [np.squeeze(baseline_data['membrane_voltage'][index])],
        'spike_times' : [baseline_data['spikes'][index]],
        'lags' : [lags],
        'corrs' : [corrs]
        }
    baseplot = pd.DataFrame(data=ba)
    return baseplot


def main():
    from ampullary_ui.analysis.utils import split_data
    data = np.load("./lif_data.npz", allow_pickle=True)
    lif_data = data["lif_data"].item()
    stim_data = data["stim_data"].item()
    simulation_params = data["sim_params"].item()
    baseline_duration = simulation_params["baseline_duration"]

    baseline, _ = split_data(lif_data, baseline_duration, stim_data["duration"])
    bf = baseline_features(baseline["spikes"], baseline["time"])
    bp = baseline_plot_data(baseline)


if __name__ == "__main__":
    main()
