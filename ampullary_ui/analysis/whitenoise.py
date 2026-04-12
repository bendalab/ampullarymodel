"""
Functions for Analysing

- Check for outliers, needed to plot isis in a comprehensible way
- Calculate serial correlation with 
- Compute firing rate by the convolution method
- Compute firing rates corresponding to different stimulus constrasts
- Compute firing rate by the convolution method for a single spike train
- Smooth a data array
- finding the nearest value in an array to a given value
- Finding the Cutoff frequency
- Finding mean values towards the end of the stimulus frequency spectrum (coherence and gain)
- Transferfunction
- Get features from Transferfunction

"""
import logging
import numpy as np
import pandas as pd
import scipy.signal as sps

from ampullary_ui.analysis.utils import convolution_rate, convolution_rate_with_std, smoothing, find_nearest


def rate_modulation(noise_responses, sigma=0.0025):
    """
    Get firing rate modulation

    Makes convolution based firing rate, computes standard deviation.

    Parameters
    ----------
    data : dictionary 
        dictionary with spikes, time and membrane_voltage only during simulation with gwn stimulation
    Returns
    -------
    fr_mods : list
        list of firing rate modulations for every simulated cell
    """
    n_neurons = len(noise_responses['spikes'])
    fr_mods= np.zeros(n_neurons)
    for i in range(n_neurons):
        if len(noise_responses['spikes'][i]) != 0:  # if there are spikes
            conv_rate = convolution_rate(noise_responses['spikes'][i], noise_responses['time'], sigma=sigma)
            fr_mod =  np.std(conv_rate)
        else:             
            fr_mod = np.NAN
        fr_mods[i] = fr_mod
    return fr_mods


def is_outlier(points, thresh=3.5):
    """
    Returns a boolean array with True if points are outliers and False otherwise.
    ---> stolen :)

    Parameters:
    -----------
        points : An numobservations by numdimensions array of observations
        thresh : The modified z-score to use as a threshold. Observations with
            a modified z-score (based on the median absolute deviation) greater
            than this value will be classified as outliers.

    Returns:
    --------
        mask : A numobservations-length boolean array.

    References:
    ----------
        Boris Iglewicz and David Hoaglin (1993), "Volume 16: How to Detect and
        Handle Outliers", The ASQC Basic References in Quality Control:
        Statistical Techniques, Edward F. Mykytka, Ph.D., Editor. 
    """
    if len(points.shape) == 1:
        points = points[:, None]
    median = np.median(points, axis=0)
    diff = np.sum((points - median)**2, axis=-1)
    diff = np.sqrt(diff)
    med_abs_deviation = np.median(diff)

    modified_z_score = 0.6745 * diff / med_abs_deviation

    return modified_z_score > thresh


def cutoff(f, Cxy):
    """
    Find Cutoff frequency

    Find the frequency at which the coherence falls to 70.71% of it's peak value

    Parameter
    ---------
    f : ndarray
        frequency in Hz
    Cxy : ndarray
        Coherence

    Returns
    -------
    cutoff_frequency : float
        cutoff frequency in Hz
    """
    idx_max = np.argmax(Cxy)
    Cxy_decline = Cxy[idx_max::]
    fraction_70 = np.max(Cxy_decline)*0.7071
    nf_70 = find_nearest(Cxy_decline, fraction_70)
    idx_cutoff = np.argmin(np.abs(Cxy_decline - nf_70)) + idx_max
    cutoff_frequency = f[idx_cutoff]
    return cutoff_frequency


def values_high_frequencies(f, values, f_lower, f_higher):
    """
    Mean coherence towards the end of the stimulus frequency spectrum

    Find nearest frquency value to lower boundery and higher boundery (150Hz in our stimulus)
    take mean over corresponding cchoerence values 

    Parameter
    ---------
    f : ndarray
        frequency in Hz
    Cxy : ndarray
        Coherence
    f_lower : float
        lower frequency boundery in Hz
    f_higher : float
        higher frequency boundery in Hz

    Returns
    -------
    highf_coh : float
        mean coherence towards the end of the stimulus frequency spectrum

    """
    # near_f_lower = find_nearest(f, f_lower)
    # near_f_higher = find_nearest(f, f_higher)
    highf_coh = np.mean(values[(f >= f_lower) & (f < f_higher)])
    # highf_values = np.mean(values[int(np.where(f == near_f_lower)[0]):int(np.where(f == near_f_higher)[0])])
    return highf_coh


def transferfunction(stimulus, rate, dt=1./20_000.):
    """
    Transferfunction

    Computes Cross spectrum of input and output signal and power spectrum of input signal
    Computes gain as cross deivided by power spectrum
    Cuts out relevent part corresponding to frequencies used in the input signal
    Smoothes transfer function

    Parameters
    ----------
    stimulus : ndarray
        stimulus size corresponding to each recorded time point, in mV/cm
    f_rate : ndarray
        firing rate in Hz corresponding to the unique stimulus values 
    dt : float
        sampling interval of dataset traces in s

    Returns
    -------
    freq : ndarray
        frequency in Hz
    tf : ndarray
        gain in Hz/mV?
    tf_smoothed _ ndarray
        smoothed gain in Hz/mV?

    """
    freq, p_yx = sps.csd(rate, stimulus, fs=1./dt,
                         nperseg=2**14, window='hann', scaling='density')
    _, p_xx = sps.welch(stimulus, fs=1./dt,
                        window='hann', nperseg=2**14, scaling='density')
    tf = abs(p_yx)/p_xx
    # cut out relevant margin
    f = freq[(freq >= 0.0) & (freq < 150.0)]
    tf = tf[(freq >= 0.0) & (freq < 150.0)]
    # smoothing
    tf_smoothed = smoothing(tf, span=4)
    return f, tf, tf_smoothed


def gain_features(freq, tf_smoothed, rate,
                  highf_min=120, highf_max=150):
    """
    Get features from the gain of the Transfer-function, extended version

    Get: 
    gain at start/0 frequency, 
    maximal gain and frequency at max gain, 
    frequency in the middle between 0 and max gain and gain at this middle frequency, 
    gain at high frequencies and the upper cutoff frequency
    in the order originally used for sbi training

    Parameters
    ----------
    freq : ndarray
        frequency in Hz
    tf_smoothed _ ndarray
        smoothed gain in Hz/mV?
    rate : np.array
        firing rate array in s

    Returns
    -------
    gain_0 : float
        gain at 0 freq
    gain_halfup : float 
        gain at half up between 0 and frequency at maximum gain of smoothed transfer function
    f_halfup : float
        frequency middle between 0 and maximum gain of smoothed transfer function
    max_gain : float
        maximum gain of smoothed transfer function
    f_at_gainmax : float 
        stimulus frequency at maximum gain of smoothed transfer function
    highf_gain : loat 
        mean gain towards the end of the stimulus frequency spectrum of smoothed transfer function
    mfr_gain : float
        gain at mean firing rate, expect peak with low contrast stimuli
    cutoff_frequency_up : float
        upper cutoff frequency in Hz
    """
    logging.debug("Analyzing gain function")
    max_gain = np.max(tf_smoothed)
    idx_max = np.where(tf_smoothed == np.max(tf_smoothed))[0][0]
    if idx_max != 0:
        tf_decline = tf_smoothed[idx_max:]
        fraction_70 = np.max(tf_smoothed)*0.7071
        nf_70_up = find_nearest(tf_decline, fraction_70)
        idx_cutoff_up = np.where(tf_decline == nf_70_up)[0][0] + idx_max
        cutoff_frequency_up = freq[idx_cutoff_up]
    else:
        fraction_70 = np.max(tf_smoothed)*0.7071
        nf_70_up = find_nearest(tf_smoothed, fraction_70)
        idx_cutoff_up = np.where(tf_smoothed == nf_70_up)[0][0]
        cutoff_frequency_up = freq[idx_cutoff_up]
    # gain at higher frequencies
    highf_gain = values_high_frequencies(freq, tf_smoothed, highf_min, highf_max)
    # gain at mean FR
    near_mean_FR = find_nearest(freq, np.mean(rate))
    mfr_gain = tf_smoothed[freq == near_mean_FR][0]
    gain_zero = tf_smoothed[0]
    f_at_gainmax = freq[tf_smoothed == max_gain][0]
    f_halfup = find_nearest(freq, f_at_gainmax*0.5)
    gain_halfup = tf_smoothed[freq == f_halfup][0]

    return gain_zero, gain_halfup, f_halfup, max_gain, f_at_gainmax, highf_gain, mfr_gain, cutoff_frequency_up


def coherence_features(freq, coherences,
                       highf_min=120, highf_max=150):
    logging.debug("Analyzing coherence function")
    fcutoff = None
    fc_max = None
    highf_coh = None
    coh_zero = None
    coh_max = None
    try:
        average_coherence = np.mean(coherences, axis=0)
        if np.isnan(coherences).all():
            raise ValueError ("Some problem with stimulation, most likely neurongroup's variable 's' has NaN, very large values, or encountered an error in numerical integration. Further features all set to NaN")
        coh_zero = average_coherence[0]
        fcutoff = cutoff(freq, average_coherence)
        fc_max = freq[np.argmax(average_coherence)]
        highf_coh = values_high_frequencies(freq, average_coherence, highf_min, highf_max)
        coh_max = np.max(average_coherence)
    except Exception as e:
        logging.error(f"An error occurred during coherence analysis {e}")

    return coh_zero, coh_max, fc_max, fcutoff, highf_coh


def get_avg_coherences(noise_responses, stimulus):
    n_neurons = len(noise_responses['spikes'])
    dt = float(noise_responses["dt"])
    stim = stimulus["stimulus"]
    coherences = []
    for i in range(n_neurons):
        if len(noise_responses['spikes'][i]) > 0:  # if there are spikes
            rates= noise_responses["rates"][i]
            collect_cxy = [[] for _ in range(len(rates))]
            cxy = []
            for j in range(len(rates)):
                f, cxy = sps.coherence(stim, rates[j, :], fs=1.0/dt,
                                       nperseg=2**14, noverlap=2**13,
                                       detrend='constant', window='hann')
                cxy_smoothed_single = smoothing(cxy, span=4) 
                collect_cxy[j] = cxy_smoothed_single
            coherences.append(collect_cxy)

    return f, coherences


def calculate_rates(noise_responses, sigma=0.0025):
    """ calculates the firing rates, and adds them to the noise_responses dict.
    """
    all_rates = []
    time = noise_responses["time"]
    for i in range(len(noise_responses["spikes"])):
        spike_trains = noise_responses["spikes"][i]
        all_rates.append(convolution_rate(spike_trains, time, sigma=sigma))
    noise_responses["rates"] = all_rates
    return noise_responses


def whitenoise_features(noise_responses, stimulus, sigma=0.0025):
    dt = float(noise_responses["dt"])
    n_neurons = len(noise_responses["spikes"])
    noise_responses = calculate_rates(noise_responses, sigma=sigma)
    rate_mod = rate_modulation(noise_responses, sigma)
    freq, coherences = get_avg_coherences(noise_responses, stimulus)

    c_features = []
    g_features = []
    for i in range(n_neurons):
        c_features.append(coherence_features(freq, coherences[i]))
        avg_rate = np.mean(np.array(noise_responses["rates"][i]), axis=0)
        f, _, tfs = transferfunction(stimulus["stimulus"], avg_rate, dt)
        g_features.append(gain_features(f, tfs, np.mean(avg_rate)))
    c_features = np.array(c_features)
    g_features = np.array(g_features)

    temp = {"fr_modulation" : rate_mod, "coh_zero": c_features[:, 0], 
            "coh_max": c_features[:, 1], "coh_highf": c_features[:, 4],
            "coh_fmax": c_features[:, 2], "coh_fcutoff" : c_features[:,3],
            "gain_zero": g_features[:, 0], "gain_halfup": g_features[:,1], 
            "gain_max": g_features[:, 3], "gain_rate": g_features[:,6],
            "gain_highf": g_features[:, 5], "gain_fhalfup": g_features[:,2],
            "fgain_max": g_features[:,4], "gain_fcutoff": g_features[:,7]}

    return temp


def whitenoise_plot_data(noise_data, stim_data,
                         contrast=0.2, sigma=0.0025, index=0):
    n_neurons = len(noise_data["spikes"])
    if index < -n_neurons or index >= n_neurons:
        raise ValueError("analysis.whitenoise.whitenoise_plot_data: invalid index!")
    stimulus_og = stim_data['stimulus']
    stim_sd = stim_data["sd"]
    scaling = contrast/stim_sd
    gwn_stimulus = stimulus_og * scaling

    # average coherence and transfer-functions
    collect_tfs = []
    collect_cxys = []
    for j in range(len(noise_data['spikes'][index])):
        trial_spikes = noise_data['spikes'][index][j]
        conv_rate = convolution_rate([trial_spikes], noise_data['time'], sigma=sigma)
        freq, _, tf_smoothed_single = transferfunction(gwn_stimulus, conv_rate, dt=1./stim_data['samplingrate'])
        collect_tfs.append(tf_smoothed_single)
        f, Cxy = sps.coherence(gwn_stimulus, conv_rate, fs=stim_data['samplingrate'], nperseg=2**14, noverlap=2**13,
                               detrend='constant', window='hann')
        Cxy_smoothed_single = smoothing(Cxy, span=4)
        collect_cxys.append(Cxy_smoothed_single)

    cxy_smoothed = np.mean(collect_cxys, axis=0)
    cxy_std = np.std(collect_cxys, axis=0)

    tf_smoothed = np.mean(collect_tfs, axis=0)
    tf_std = np.std(collect_tfs, axis=0)

    # mean convolution rate and associates
    conv_rate, conv_std = convolution_rate_with_std(noise_data['spikes'][index], noise_data['time'], sigma=sigma) 

    stim_plot = {
        'spike_times' : noise_data['spikes'], 
        'stimulus' : [stim_data['stimulus']], 
        'stimulus_time' :  [noise_data['time']], 
        'conv_rate' : [conv_rate], 
        'conv_std' : [conv_std], 
        'stimulus_freq' : [f], 
        'coherence_smooth' : [cxy_smoothed], 
        'coherence_std' : [cxy_std],
        'tf_f' : [freq],
        'tf_smoothed' : [tf_smoothed],
        'tf_std' : [tf_std], 
        }
    df = pd.DataFrame(data=stim_plot)
    return df