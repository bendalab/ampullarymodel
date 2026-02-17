"""
LIF model
+ refractory time
+ offset current
+ noice
+ stimulus gain factor
+ dentritic filter
+ adapation:
    - tau a
    - delta a
    - noise a
"""
from brian2 import *

defaultclock.dt = 50*us


def lif_simulation(params, stimulus, stimulus_length=200.0, mv=False):
    """
    Lif Simulation Version 08

    Simulates leaky integrate-and-fire model (LIF) with Brian2 for parameter sets in params
    - membrane time constant
    - offset current
    - strength of noise 
    - refractory time
    - stimulus gain factor
    - tau dentritic
    - tau adapation
    - increment adaptation at spike event 
    - strength of adaptation noise
    during baseline activity/no stim situation and gwn stimulation

    Parameters
    ----------
    params : np.array
        values for membrane time constant, offset current, strength of noise, refractory time, stimulus gain factor, tau dentritic, tau adapation, increment adaptation at spike event 
    stimulus : TimedArray
        stimulus size corresponding to each time point, unit-less as a function of time
    stimulus_length : float
        length of white noise stimulus in seconds, default is 100.00005 (len(stimulusx10)+defaultclock.dt)
    mv : bool
        decision whether membrane voltage should be included in the return dict. Default is False 

    Returns
    -------
    data : dictionary 
        dictionary with spike_idx, spike_times, time and membrane_voltage, depending on mv input
    """

    # fixed parameters
    #print(params, params.shape)
    vr = 0.0             # resting potential [mV]
    vt = 1.0             # firing threshold [mV] 
    t_adaption = 1000*ms  # time for adaption before recording 
    duration = 30*second + stimulus_length*second    # runtime
 

    # equation for membrane voltage 
    eqs = '''
     dv/dt = (( - v + offset + D*randn() + gain*s - i_a) /tau) : 1 (unless refractory)
     ds/dt = (- s + stimulus(t))/ tau_d : 1 
     di_a/dt = (- i_a + D_adapt*randn()) / tau_a : 1

    # parameters 
    tau : second (constant)
    ref : second (constant)
    offset : 1 (constant)
    D : 1 (constant)
    gain : 1 (constant)
    tau_d : second (constant)
    tau_a : second (constant)
    delta : 1 (constant)
    D_adapt : 1 (constant)
    '''

    
    # simulaton 
    neurons = NeuronGroup(params.shape[0], eqs, threshold='v>vt', reset='v = vr; i_a += delta', refractory='ref', method='euler')
    # starting values for v 
    neurons.v = vr  # Would be the solution when dv/dt = 0

    # for every neuron different parameters
    neurons.tau = params[:,0]*ms          # membrane time_constant [ms]
    neurons.ref = params[:,1]*ms          # refractory time [ms]
    neurons.offset = params[:,2]          # offset current [nA]
    neurons.D = params[:,3]               # strength of noise, unitless
    neurons.gain = params[:,4]            # stimulus gain factor, unitless 
    neurons.tau_d = params[:,5]*ms        # tau dentritic
    neurons.tau_a = params[:,6]*ms        # tau adapation
    neurons.delta = params[:,7]           # increment adaptation at spike event 
    neurons.D_adapt = params[:,8]         # adaptation noise strength 
    
    # discard first second 
    run(t_adaption)

    # run and record
    statemon = StateMonitor(neurons, 'v', record = True)
    spikemon = SpikeMonitor(neurons, record = True)
    run(duration)

    if mv==False:
        data = dict(
        n_neurons = len(params),
        spike_idx = np.asarray(spikemon.i),
        spike_times = spikemon.t/ms - (t_adaption/ms),
        time = statemon.t/ms - (t_adaption/ms))
    elif mv==True:
        data = dict(
        n_neurons = len(params),
        spike_idx = np.asarray(spikemon.i),
        spike_times = spikemon.t/ms - (t_adaption/ms),
        time = statemon.t/ms - (t_adaption/ms), 
        membrane_voltage = statemon.v,
        )
    return data


