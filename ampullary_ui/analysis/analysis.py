import numpy as np
import pandas as pd

from ampullary_ui.analysis.utils import split_data, spiketimes_to_trials
import ampullary_ui.analysis.baseline as bs
import ampullary_ui.analysis.whitenoise as wn


def summary_statistics(lif_data, stim_data, baseline_duration=30., sigma=0.0025):
    """
    Calculates summary statistics 

    Calculates summary statistics from spike data of cell simulations:
    - mean firing rate
    - interspikeintervall CV
    - first lag of the serial Correlation
    - frequency modulation
    - frequency coherence features: cutoff frequency, frequency at max coherence, max coherence, coherence at high frequencies and coherence at 0 Hz
    - transferfunction featurers : Gain at 0 Hz, gain halfway between 0 Hz and frequency of max. gain, frequency halfway between 0 Hz and frequency of max. gain, maximal gain, frequency at maximal gain, gain at cell's own mean firing rate, gain at high frequencies and cutoff frequency of descent


    Parameters
    ----------
    data : dict
        dictionary with spike_idx, spike_times and time
    stim_data : dict
        dictionary that includes stimulus itself, as well as meta data and time array 
        
    Returns
    -------
    sum_stats : np.array
        tensor of summary statistics
    """
    features = {}
    baseline, noise = split_data(lif_data, baseline_duration, stim_data["duration"])
    basline_feats = bs.baseline_features(baseline["spikes"], baseline["time"])
    features.update(basline_feats)

    noise_trials = spiketimes_to_trials(noise)
    noise_feats = wn.whitenoise_features(noise_trials, stim_data,sigma)
    features.update(noise_feats)
    df = pd.DataFrame(features)

    return df


def main():
    data = np.load("lif_data.npz", allow_pickle=True)
    lif_data = data["lif_data"].item()
    stim_data = data["stim_data"].item()
    simulation_params = data["sim_params"].item()
    baseline_duration = simulation_params["baseline_duration"]

    df = summary_statistics(lif_data, stim_data, baseline_duration)
    print(df)


if __name__ == "__main__":
    main()
