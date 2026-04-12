"""
# used in run_simulations (for plot data and features)

Functions helping to analyse the cell models 
- Extract baseline features and baseline plotting arrays
- Extract white noise response features and white noise response plotting arrays
"""
import numpy as np
import pandas as pd 
import scipy.signal as sps 
from ampullary_ui.analysis.whitenoise import transferfunction, smoothing, gain_features, coherence_features
from ampullary_ui.analysis.baseline import serial_correlations
from ampullary_ui.analysis.utils import convolution_rate_single, convolution_rate_with_std

from ampullary_ui.utils import load_common_variables


common_variables = load_common_variables()

def analyze_baseline_data(data):
    """
    Extract baseline features

    Computes firing rate, ISI CV, and first lag seriel correlation for a single simulated cell model.
    Also collects relevant arrays for plotting baseline features in a dataframe (since it's faster to do this in one go).

    Parameters 
    ----------
    data : dictionary 
        dictionary with spikes, time and membrane_voltage only during simulation without stimulation

    Return
    ------
    baseparams : list
        List of baseline features: mean firing rate, interspikeintervall coefficient of variation and first lag of the seriel correlation
    baseplot : Dataframe
        pandas Dataframe of relevent arrays needed to visuialize the baseline features
    """
    counts = np.asarray([len(i) for i in data['spikes']])
    frates = counts/(np.round(data['time'][-1]-  data['time'][0]))
    isis = [np.diff(i) for i in data['spikes']] 
    isi_cvs = [np.std(i)/np.mean(i) for i in isis]
    n_neurons = len(data['spikes'])
    corrs_arr = np.zeros(n_neurons)
    for i in range(n_neurons):
        lags, corrs = serial_correlations(data['spikes'][i], max_lag=10)
        corrs_arr[i] = corrs[1]
    baseparams = [frates[0], isi_cvs[0], corrs_arr[0]]
    ba = {
        'membrane_time' : [data['time']],
        'membrane_voltage' : [np.squeeze(data['membrane_voltage'])],
        'spike_times' : data['spikes'],
        'lags' : [lags],
        'corrs' : [corrs]
        }

    baseplot = pd.DataFrame(data=ba)
    return baseparams, baseplot


def analyze_noise_data(data, stim_data):
    """
    Extract features from white noise stimulation

    Computes firing rate modulation, characterizing features of the frequency coherence plot and characterizing features of the gain of the transfer function. 
    Also collects relevant arrays for visualizing white noise stimulation features in a dataframe.
    Parameters 
    ----------
    data : dictionary 
        dictionary with spikes and time during simulation with white noise stimulation
    stim_data : dictionary   
        dictionary with stimulus as well as meta data concerning the stimulus used during white noise stimulation
    
    Return
    ------
    stimparams : list
        List of white noise stimulation features: firing rate modulation, characterizing features of the frequency coherence plot and characterizing features of the gain of the transfer function. 
    stimplot : Dataframe
        pandas Dataframe of relevent arrays needed to visuialize the features of the white noise stimulation
    """
    stimulus_og = stim_data['stimulus']
    wanted_sd = 0.2     #FIXME hardcode
    stim_sd = stim_data["sd"]

    scaling = wanted_sd/stim_sd
    gwn_stimulus = stimulus_og * scaling

    # average coherence and transfer-functions
    collect_tfs = [[] for _ in range(len(data['spikes'][0]))]
    collect_cxys = [[] for _ in range(len(data['spikes'][0]))]
    for j in range(len(data['spikes'][0])):
        spike_section = data['spikes'][0][j]
        conv_rate = convolution_rate_single(spike_section, data['time'])
        freq, _, tf_smoothed_single = transferfunction(gwn_stimulus, conv_rate, stim_data['samplingrate'])
        collect_tfs[j] = tf_smoothed_single
        f, Cxy = sps.coherence(gwn_stimulus, conv_rate, fs=stim_data['samplingrate'], nperseg=2**14, noverlap=2**13,
                               detrend='constant', window='hann')
        Cxy_smoothed_single = smoothing(Cxy, span=4)
        collect_cxys[j] = Cxy_smoothed_single

    cxy_smoothed = np.mean(collect_cxys, axis=0)
    cxy_std = np.std(collect_cxys, axis=0)

    tf_smoothed = np.mean(collect_tfs, axis=0)
    tf_std = np.std(collect_tfs, axis=0)

    coh_zero, coh_max, fc_max, fcutoff, highf_coh = coherence_features(f, collect_cxys)
    gain_0, gain_halfup, f_halfup, max_gain, f_at_gainmax, highf_gain, mfr_gain, cutoff_frequency_up = gain_features(freq, tf_smoothed, conv_rate)

    # mean convolution rate and associates
    conv_rate, conv_std = convolution_rate_with_std(data['spikes'][0], data['time'], sigma=common_variables['sigma_conv_rate']) 
    fr_mod = np.std(conv_rate)

    # collect features
    stimparams =[fr_mod, coh_zero, coh_max, highf_coh, fc_max, fcutoff,    
                 gain_0, gain_halfup, max_gain, mfr_gain, highf_gain, f_halfup, f_at_gainmax, cutoff_frequency_up]

    # make dictionary for stimulation plot
    stim_plot = {
        'spike_times' : data['spikes'], 
        'stimulus' : [stim_data['stimulus']], 
        'stimulus_time' :  [data['time']], 
        'conv_rate' : [conv_rate], 
        'conv_std' : [conv_std], 
        'stimulus_freq' : [f], 
        'coherence_smooth' : [cxy_smoothed], 
        'coherence_std' : [cxy_std],
        'tf_f' : [freq],
        'tf_smoothed' : [tf_smoothed],
        'tf_std' : [tf_std], 
        }

    stimplot = pd.DataFrame(data=stim_plot)
    return stimparams, stimplot
