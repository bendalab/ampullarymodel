"""
LIF model
+ refractory time
+ offset current
+ noise
+ stimulus gain factor
+ dendritic filter
+ adaptation:
    - tau a
    - delta a
    - noise a
"""
import numpy as np
import pandas as pd

from brian2 import TimedArray, NeuronGroup, StateMonitor, SpikeMonitor, defaultclock, run
from brian2.units import ms, us, second

from pathlib import Path

defaultclock.dt = 50*us


def package_parameters(parameters, package_size=100):
    """
    Chop parameters table into packages 

    Chop table of parameters sets into packages of package_size + residual.
    Needed for simulation with brian2, since I simulate parallel. This ensures it is at max 100 neurons that are
    simulated at the same time and the simulations doesn't need too much RAM.
    --> change package size for strong computers if many cells need to be simulated

    Parameters
    ----------   
    parameters: pd.Dataframe
        parameter table as loaded with pandas
    param package_size: int
        package size, default = 100

    Returns
    -------
    packages : list of list of arrays
        list of packages of max 100 model parameter sets
    """

    params = parameters.to_numpy()
    n_rows = params.shape[0]
    packages = []
    for start in range(0, n_rows, package_size):
        chunk = params[start:start + package_size]
        packages.append((start, chunk))
    return packages


def ampullary_lif(params, stimulus, prerun_duration=1.0, record_voltage=False):
    """
    Lif Simulation Version 08

    Simulates leaky integrate-and-fire model (LIF) with Brian2 for parameter sets in params
    - membrane time constant
    - offset current
    - strength of noise 
    - refractory time
    - stimulus gain factor
    - tau dendritic
    - tau adaptation
    - increment adaptation at spike event 
    - strength of adaptation noise

    Parameters
    ----------
    params : np.array
        shape (n, 9). First dimension is the number of parallel simulations, second dimension the model parameters.
        (1) membrane time constant (2) offset current (3) strength of intrinsic noise, 4) refractory time, (5) stimulus gain factor, (6) tau dendritic, (7) tau adaptation, (8) adaptation increment at spike event, and (9) the adaptation noise. 
    stimulus : TimedArray
        stimulus size corresponding to each time point, unit-less as a function of time
    prerun_duration: float
        Additional time the simulation should be allowed to run without being recorded. The pre-run data is discarded. defaults t0 1.0s
    record_votage : bool
        decision whether membrane voltage should be included in the return dict. Default is False 

    Returns
    -------
    data : dictionary 
        dictionary with spike_idx, spike_times, time and membrane_voltage, depending on mv input
    """
    timed_stimulus = TimedArray(stimulus, defaultclock.dt)

    vr = 0.0             # resting potential [mV]
    vt = 1.0             # firing threshold [mV] 
    prerun_duration = prerun_duration * second  # pre-recording duration
    total_duration = timed_stimulus.values.shape[0] * timed_stimulus.dt * second

    # equation for membrane voltage
    eqs = '''
     dv/dt = (( - v + offset + D*randn() + gain*s - i_a) /tau) : 1 (unless refractory)
     ds/dt = (- s + timed_stimulus(t))/ tau_d : 1 
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

    # initialize simulation
    neurons = NeuronGroup(params.shape[0], eqs, threshold='v>vt', reset='v = vr; i_a += delta',
                          refractory='ref', method='euler')
    # starting values for v 
    neurons.v = vr  # Would be the solution when dv/dt = 0
    neurons.tau = params[:,0]*ms          # membrane time_constant [ms]
    neurons.ref = params[:,1]*ms          # refractory time [ms]
    neurons.offset = params[:,2]          # offset current [nA]
    neurons.D = params[:,3]               # strength of noise, unitless
    neurons.gain = params[:,4]            # stimulus gain factor, unitless
    neurons.tau_d = params[:,5]*ms        # tau dendritic
    neurons.tau_a = params[:,6]*ms        # tau adaptation
    neurons.delta = params[:,7]           # increment adaptation at spike event
    neurons.D_adapt = params[:,8]         # adaptation noise strength

    # discard pre-run duration
    run(prerun_duration)

    # run and record
    statemon = StateMonitor(neurons, 'v', record = True)
    spikemon = SpikeMonitor(neurons, record = True)
    run(total_duration - prerun_duration)

    data = dict(n_neurons = len(params),
                spike_idx = np.asarray(spikemon.i),
                spike_times = spikemon.t/second - (prerun_duration/second),
                time = statemon.t/second - (prerun_duration/second),
                dt = defaultclock.dt)
    if record_voltage:
        data["membrane_voltage"] = statemon.v
    return data


def main():
    from ampullary_ui.utils import load_gwnstimulus, modify_stimulus

    baseline_duration = 30
    prerun_duration = 1.0
    trials = 10
    contrast = 0.2

    stimulus = Path.cwd() / "stimuli" / "gwn150Hz10s0.3.dat"
    parameter_table = Path.cwd() / "examples" / "example_parameters_short.csv"
    stim = load_gwnstimulus(filename=stimulus)
    stimulus = modify_stimulus(stim, baseline_duration, prerun_duration, trials, contrast)
    parameters = pd.read_csv(parameter_table)
    params = package_parameters(parameters)
    lif_data = ampullary_lif(params[0][1], stimulus, prerun_duration, False)
    np.savez("./lif_data.npz", lif_data=lif_data, stim_data=stim,
             model_params=parameters, 
             sim_params={"baseline_duration": 30, "prerun_duration": 1.0,
                        "trials": 10, "contrast": 0.2},
             allow_pickle=True)


if __name__ == "__main__":
    main()
