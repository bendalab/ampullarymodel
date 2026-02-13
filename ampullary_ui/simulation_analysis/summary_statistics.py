"""
Functions for extracting summary statistics from simulated data


- Extract baseline features extended: firing rate, ISI CV and first lag serial correlation for every simulated cell 
- Computes firing rate modulation for every cell 
- Computes frequency coherence for every cell and extracts features
- Computes features from Transferfunction
- Calculate summary statistics from spike data for simulated date
"""
import numpy as np
import scipy.signal as sps
from brian2.units.allunits import second
from computations.lif_simulation import defaultclock
from computations.stimulus_helper import stimulus_scaling_artificial
from simulation_analysis.convert_data import seperate_data, relativ_stimulation_times
from simulation_analysis.analysis_helpers import serial_correlations, smoothing, cutoff, convolution_rate, convolution_rate_single, values_high_frequencies, transferfunction, tf_features





def baseline_features(data):
    """
    Extract baseline features

    Computes firing rate, ISI CV and first lag correlation  for every simulated cell 

    Parameters 
    ----------
    data : dictionary 
        dictionary with spikes, time and membrane_voltage only during simulation without stimulation
    
    Return
    ------
    frates : np.array
        mean firing rate of every simulated cell
    isi_cv : np.array
        Interstimulusintervall CV of every simulated cell
    corrs_arr : np.array
        first lag correlation of every simulated cell

    """
    counts = np.asarray([len(i) for i in data['spikes']])
    frates = counts/(np.round(data['time'][-1]-  data['time'][0]))
    isis = [np.diff(i) for i in data['spikes']] 
    isi_cvs = [np.std(i)/np.mean(i) for i in isis]
    isi_cvs = np.array(isi_cvs)
    n_neurons = len(data['spikes'])
    corrs_arr = np.zeros(n_neurons)
    for i in range(n_neurons):
        _, corrs = serial_correlations(data['spikes'][i], max_lag=10)
        corrs_arr[i] = corrs[1]
    return frates, isi_cvs, corrs_arr 


def get_fr_mod_sim(data):
    """
    Get firing rate modulation

    Makes convolution based firing rate, computes standart deviation.


    Parameters
    ----------
    data : dictionary 
        dictionary with spikes, time and membrane_voltage only during simulation with gwn stimulation
    Returns
    -------
    fr_mods : list
        list of firing rate modulations for every simulated cell
    """
    n_neurons = len(data['spikes'])
    fr_mods= np.zeros(n_neurons)
    for i in range(n_neurons):
        if len(data['spikes'][i]) != 0:  # if there are spikes
            conv_rate = convolution_rate(data['spikes'][i], data['time'])
            fr_mod =  np.std(conv_rate)
        else:             
            fr_mod = np.NAN
        fr_mods[i] = fr_mod
    return fr_mods
    



def get_coherence_features_sim(data, stimulus):
    """
    Get featues of frequency coherence 

    Makes convolution based firing rate, computes coherence depending on stimulus frequency and returns coherence features:
    - cutoff frequency
    - frequency at max coherence
    - max coherence
    - coherence at high frequencies 
    - coherence at 0 Hz
    

    Parameter
    ---------
    data : dictionary 
        dictionary with spikes, time and membrane_voltage only during simulation with gwn stimulation
    stimulus : np.array(n,)
        stimulus size corresponding to each time point, unit-less
 
    Returns
    -------
    coh_params : list
        list of arrays with frequency coherence features
    """
    #firing rate over time
    n_neurons = len(data['spikes'])
    coh_params = [ [] for _ in range(n_neurons) ]
    cxys = [ [] for _ in range(n_neurons) ]
    worked = 0
    nofeatures = 0
    workednot = 0

    for i in range(n_neurons):
        if len(data['spikes'][i]) != 0:  # if there are spikes
            collect_cxy = [[] for _ in range(len(data['spikes'][i]))]   
            for j in range(len(data['spikes'][i])):
                spike_trial = data['spikes'][i][j]
                conv_rate = convolution_rate_single(spike_trial, data['time'])
                f, cxy = sps.coherence(stimulus, conv_rate, fs=1.0/(defaultclock.dt/second) , nperseg=2**14, noverlap=2**13, detrend='constant', window='hann') 
                cxy_smoothed_single = smoothing(cxy, span=4) 
                collect_cxy[j] = cxy_smoothed_single
            cxy_smoothed = np.mean(collect_cxy, axis=0)
            try:
                # find cutoff frequency
                fcutoff = cutoff(f, cxy_smoothed)
                # frequency at max coherence
                c_max = np.max(cxy_smoothed)
                fc_max = f[np.where(cxy_smoothed == c_max)[0][0]]
                # coherence at high frequencies
                highf_coh = values_high_frequencies(f, cxy_smoothed, 120.0, 150.0)
                # coherence at 0 Hz
                coh_zero = cxy_smoothed[0]
                worked += 1
            except: 
                fcutoff = np.NAN
                c_max = np.NAN
                fc_max = np.NAN
                highf_coh = np.NaN
                coh_zero = np.NaN
                nofeatures += 1
        else:             
            fcutoff = np.NAN
            c_max = np.NAN
            fc_max = np.NAN
            highf_coh = np.NaN
            coh_zero = np.NaN
            cxy_smoothed = np.NaN
            f = np.NaN   
            workednot += 1
        coh_params[i] = [fcutoff, fc_max,  c_max, highf_coh, coh_zero]
    return coh_params

    

def get_tf_features_sim(data, stimulus):
    """
    Get features from Transferfunction

    Makes convolution based firing rate, computes the transferfunction and computes and returns transfer function features:
    - Gain at 0 Hz
    - gain halfway between 0 Hz and frequency of max. gain
    - frequency halfway between 0 Hz and frequency of max. gain
    - maximal gain
    - frequency at maximal gain
    - gain at cell's own mean firing rate
    - gain at high frequencies
    - cutoff frequency of descent


    Parameters
    ----------
    data : dict
        dictionary with spikes, time and membrane_voltage only during simulation with gwn stimulation
    stimulus : np.array(n,)
        stimulus size corresponding to each time point, unit-less
   
    Returns
    -------
    tf_params : list
        list of arrays with transfer function features 
    """
    n_neurons = len(data['spikes'])
    tf_params = [ [] for _ in range(n_neurons) ]
    tfs = [ [] for _ in range(n_neurons) ]
    for i in range(n_neurons):
        if len(data['spikes'][i]) != 0:  # if there are spikes
            collect_tfs = [[] for _ in range(len(data['spikes'][i]))]   
            for j in range(len(data['spikes'][i])):
                spike_trial = data['spikes'][i][j]
                conv_rate = convolution_rate_single(spike_trial, data['time'])
                freq, _, tf_smoothed_single = transferfunction(stimulus, conv_rate, 1.0/(defaultclock.dt/second))
                collect_tfs[j] = tf_smoothed_single
            tf_smoothed = np.mean(collect_tfs, axis=0)
            conv_rate = convolution_rate(data['spikes'][i], data['time']) # das hier ist unnötig und geht auch besser...
            gain_0, gain_halfup, f_halfup, max_gain, f_at_gainmax, highf_gain, mfr_gain, cutoff_frequency_up = tf_features(freq, tf_smoothed, conv_rate)
        else:   
            gain_0 = np.NAN
            gain_halfup = np.NAN
            f_halfup = np.NAN        
            max_gain = np.NAN
            f_at_gainmax = np.NAN
            highf_gain = np.NAN
            mfr_gain = np.NaN
            cutoff_frequency_up = np.NaN
        tf_params[i] = [gain_0, gain_halfup, f_halfup, max_gain, f_at_gainmax, mfr_gain, highf_gain, cutoff_frequency_up]
    return tf_params

    

def calculate_sum_stats(data, stim_data,):
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
    # make spikelists 
    n_neurons = data['n_neurons']
    sum_stats = [ [] for _ in range(n_neurons)]
    #seperate data
    baseline, stimulation = seperate_data(data, stim_data['baseline_recording']) # includes spike convert
    # baseline_properties
    frates, isi_cvs, scorr1= baseline_features(baseline)
    # gwn stimulation
    rel_stimulation = relativ_stimulation_times(stimulation, stim_data['baseline_recording'])
    gwn_stimulus = stimulus_scaling_artificial(stim_data['stimulus'])
    fr_mod = get_fr_mod_sim(rel_stimulation)
    coh_params = get_coherence_features_sim(rel_stimulation, gwn_stimulus)
    tf_params = get_tf_features_sim(rel_stimulation, gwn_stimulus)
    # add up
    for i in range(n_neurons):
        sum_stats[i] = [frates[i], isi_cvs[i], scorr1[i], fr_mod[i]] + coh_params[i] + tf_params[i]    
    sum_stats = np.array(sum_stats)
    return sum_stats


