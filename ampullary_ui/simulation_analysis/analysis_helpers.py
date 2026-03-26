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
import scipy.signal as sps
from scipy.stats import norm

from ampullary_ui.utils import load_common_variables


common_variables = load_common_variables()


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


def convolution_rate(spike_times, time, sigma=common_variables['sigma_conv_rate']):
    """
    Firing rate computed by the convolution method.

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
        Firing rate corresponding to spikes in Hz.

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
    return conv_rate


def convolution_rate_with_std(spike_times, time, sigma=common_variables['sigma_conv_rate']):
    """
    Firing rate computed by the convolution method + STD.

    Makes a binary spike train with the length of the measured time out of the 
    spike times and uses a Gaussian Kernel for convolution. Also computes standart deviation

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
        standart deviation
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


def convolution_rate_single(spike_times, time, sigma=common_variables['sigma_conv_rate']):
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

    Smooths data via convolution, with kernel span*2+1, replicates first and last entry to even out filter efect of smoothing

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


def transferfunction(stimulus, f_rate, samplingrate):
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
    samplingrate : float
        samplingrate of dataset traces in Hz

    Returns
    -------
    freq : ndarray
        frequency in Hz
    tf : ndarray
        gain in Hz/mV?
    tf_smoothed _ ndarray
        smoothed gain in Hz/mV?

    """
    freq, p_yx = sps.csd(f_rate, stimulus, fs=samplingrate,
                         nperseg=2**14, window='hann', scaling='density')
    _, p_xx = sps.welch(stimulus, fs=samplingrate,
                        window='hann', nperseg=2**14, scaling='density')
    tf = abs(p_yx)/p_xx
    # cut out relevant margin
    freq = freq[np.where((freq >= 0.0) & (freq <= 150.0))[0]]
    tf = tf[np.where((freq >= 0.0) & (freq <= 150.0))[0]]
    # smoothing
    tf_smoothed = smoothing(tf, span=4)
    return freq, tf, tf_smoothed


def gain_features(freq, tf_smoothed, rate, highf_min=120, highf_max=150):
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
    gain_0 = tf_smoothed[0]
    f_at_gainmax = freq[tf_smoothed == max_gain][0]
    f_halfup = find_nearest(freq, f_at_gainmax*0.5)
    gain_halfup = tf_smoothed[freq == f_halfup][0]

    return gain_0, gain_halfup, f_halfup, max_gain, f_at_gainmax, highf_gain, mfr_gain, cutoff_frequency_up


def coherence_features(freq, coherences, highf_min=120, highf_max=150):
    logging.debug("Analyzing coherence function")
    fcutoff = None
    fc_max = None
    highf_coh = None
    coh_zero = None
    coh_max = None
    try:
        average_coherence = np.mean(coherences, axis=0)
        if np.isnan(coherences).all():
            raise ValueError ("Some problem with simulating stimulation, most likely neurongroup's variable 's' has NaN, very large values, or encountered an error in numerical integration. Further features all set to NaN")
        coh_zero = average_coherence[0]
        fcutoff = cutoff(freq, average_coherence)
        fc_max = freq[np.argmax(average_coherence)]
        highf_coh = values_high_frequencies(freq, average_coherence, highf_min, highf_max)
        coh_max = np.max(average_coherence)
    except Exception as e:
        logging.error(f"An error occurred during coherence analysis {e}")

    return coh_zero, coh_max, fc_max, fcutoff, highf_coh
