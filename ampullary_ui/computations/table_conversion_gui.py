"""
Functions for Table extentions:

- Chop parameters table into packages 
- Convert raw simulation data into pre-processed data format and save data
- Worker function for running a single LIF simulation in a multiprocessing setup.
- Load posterior
- Convert feature table into usable format and order
- Worker function for generating a model sample from a posterior distribution in a multiprocessing setup.
"""

import pickle
import os
import json
import numpy as np
from brian2 import TimedArray
from computations.lif_simulation import lif_simulation, defaultclock
from simulation_analysis.summary_statistics import calculate_sum_stats
from simulation_analysis.convert_data import seperate_data, relativ_stimulation_times
from IPython import embed




def package_parameters(parameters, package_size=100):
    """
    Chop parameters table into packages 

    Chop table of parameters sets into packages of package_size + restsidual.
    Needed for simulating with brian2, since I simulate parallel. This ensures its max 100 neurons that are
    simulated on the same time and the simulations doesn't need much RAM.
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



def wrap_and_save_data(sim_data, stim_data, save_dir, params, start_idx):
    """
    Convert raw simulation data into pre-processed data format and save data

    Seperate simulated data of baseline activity from simulated data during stimulation with gwn
    Compute spike times relative to stimulus start for all repetitions of the stimulation
    Pack together and save as .npz
    
    sim_data: dictionary 
        dictionary with spike_idx, spike_times and time array
    stim_data : dict
        GWN Stimulus used for training, dictionary includes stimulus itself, as well as meta data and time array
    save_dir: str
        Directory path where simulation data will be stored
    params : np.array
        array of arrays with model parameter sets
    start_idx : int
        Index identifying the current simulation job for naming saved files.

    Returns
    -------
    True : bool
        check for "ran"
    """
    baseline, stimulation = seperate_data(sim_data, stim_data['baseline_recording'])
    rel_stimulation = relativ_stimulation_times(stimulation, stim_data['baseline_recording'])
    for i in range(len(rel_stimulation['spikes'])):
        # Create a stable identifier
        cell_id = start_idx + i
        filepath = save_dir / f"cell_{cell_id}.npz"
        np.savez_compressed(
        filepath,
        baseline_time=np.round(baseline['time'], 7),
        baseline_spikes=baseline['spikes'][i],
        whitenoise_time=np.round(rel_stimulation['time'], 7),
        whitenoise_spikes=np.array(rel_stimulation['spikes'][i], dtype=object),  # list of arrays
        params=params[i])
    return True


def worker_function_simulate_multi(start_idx, package, stimulus, stim_data, stimulus_length, 
                                   result_queue, progress_queue, save_raw, calc_feats, save_dir):
    """
    Worker function for running a single LIF simulation in a multiprocessing setup.

    This function wraps the full simulation pipeline for one parameter package (max 100 sets):
    it generates a timed stimulus, runs the LIF simulation, optionally saves minimally pre-processed simulation data, optionally computes features,
    and communicates results back through multiprocessing queues.

    Parameters
    ----------
    start_idx : int
        Index identifying the current simulation job for naming saved files.
    packages : list of list of arrays
        list of packages of max 100 model parameter sets for `lif_simulation`
    stimulus : np.array
        stimulus size corresponding to each time point, dt = default 50us
        Input stimulus array to be converted into a `TimedArray` and passed to the simulation.
    stim_data : dict
        GWN Stimulus used for training, dictionary includes stimulus itself, as well as meta data and time array
    stimulus_length : float
        Duration of the stimulus used in the simulation.
    result_queue : multiprocessing.Queue
        Queue used to return results to the parent process. On success,
        a dictionary with keys:
            - "features": computed summary statistics or None
            - "saved_flag": bool indicating whether raw data was saved
        On failure, `None` is placed in the queue.
    progress_queue : multiprocessing.Queue
        Queue used to report progress or error messages to the parent process.
    save_raw : bool
        If True, raw simulation output is wrapped and saved to disk.
    calc_feats : bool
        If True, summary statistics are computed from the simulation output.
    save_dir : str
        Directory path where simulation data will be stored if`save_raw` is True.

    Returns
    -------
    None
        Results are returned via `result_queue`. Errors are reported via `progress_queue`.
    """
    
    saved_flag = False
    features = None
    try:
        timed_stimulus = TimedArray(stimulus, defaultclock.dt)  
        sim_data = lif_simulation(package, timed_stimulus, stimulus_length=stimulus_length, mv=False)
        if save_raw:
            saved_flag = wrap_and_save_data(sim_data, stim_data, save_dir, package, start_idx)
        if calc_feats:
            features = calculate_sum_stats(sim_data, stim_data)
        del sim_data
        result_queue.put({"features": features, "saved_flag": saved_flag})
    except Exception as e:
        progress_queue.put(f'Error: {str(e)}')
        result_queue.put(None)


def load_posterior():
    """
    Load the posterior

    Parameters
    ----------
    None

    Returns
    -------
    posterior : DirectPosterior
        Posterior p(θ|x) with .sample() and .log_prob() methods from training with LIF Model.
    """
    filepath = os.path.join("..", "source", "posterior.pkl")
    with open(filepath, 'rb') as handle:
        posterior = pickle.load(handle)
    return posterior


def prepare_feature_inputs(wanted_cells):
    """
    Convert feature table into usable format and order

    Parameters
    ----------    
    wanted_cells : pd.Dataframe
        table of feature sets representing wanted cells, columns in "human logic" order

    Returns
    -------
    rel_stats : np.array
        array of arrays with features, in the same order as use for sbi training
    """
    filepath = os.path.join("general_helpers", "new_order.json")
    with open(filepath, "r") as file:
        new_order = json.load(file)['new_order']
    back_to_original = np.argsort(new_order)
    df_resorted = wanted_cells.iloc[:, back_to_original]
    rel_stats = df_resorted.to_numpy()
    return rel_stats


def worker_function_generate_multi(row, posterior, result_queue, progress_queue):
    """
    Worker function for generating a model sample from a posterior distribution in a multiprocessing setup.

    This function sets the posterior's default input using the provided row, performs MAP estimation, and returns the resulting parameter vector
    through a multiprocessing queue.

    Parameters
    ----------
    row : np.array
        single feature set
    posterior : DirectPosterior
        Posterior p(θ|x) with .sample(), .map() and .log_prob() methods from training with LIF Model.
    result_queue : multiprocessing.Queue
        Queue used to return results to the parent process. On success, the estimated model parameters (np.array) are placed in the queue. 
        On failure, `None` is placed in the queue.
    progress_queue : multiprocessing.Queue
        Queue used to report progress updates or error messages to the parent process.

    Returns
    -------
    None
        The resulting MAP estimate is returned via `result_queue`.
        Errors are reported via `progress_queue`.
    """
    try:
        progress_queue.put(f'Starting cell computation...')
        p = posterior.set_default_x(row)
        mapped_posterior = p.map(num_iter=1000, show_progress_bars=False)
        model = np.array(mapped_posterior.numpy())[0]#[0]
        result_queue.put(model)
    except Exception as e:
        progress_queue.put(f'Error: {str(e)}')
        result_queue.put(None)
