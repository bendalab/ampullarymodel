"""
Logic functions for implementing user interactions

- Simulate a neuron from a single set of model parameter
- Get MAP model for a single set of cell features
"""

import json
import os
import pickle
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, Any
from computations.lif_simulation import lif_simulation
from computations.stimulus_helper import load_simulation_stimulus
from simulation_analysis.convert_data import seperate_data_incl_membvol, relativ_stimulation_times
from simulation_analysis.analyse_sim_data import sim_baseline_data, sim_gwn_data

from IPython import embed


@dataclass
class SimulationResult:
    data: Dict[str, Any]               # simulation data dictionary
    features: np.ndarray               # analysis output features array
    baseplot: pd.DataFrame             # DataFrame for baseplot data
    stimplot: pd.DataFrame             # DataFrame for stimulation plot data



def simulate_from_input_params(params):
    """
    Simulate a neuron from a single set of model parameter

    Get a set of model parameter by asking the user for it vio GUI and use the extended LIF model to simulate it. 
    Compute features, plot it to visualize and return simulated data.

    --> return or save the resulting parameter set.
    --> saving plot should be optional/connected to a button

    Parameters
    ----------
    params : list(? check)
        model parameter set
    
    Returns
    -------
    SimulationResult : dataclass   
        simulation data dictionary, analysis output features array, DataFrame for baseplot data, DataFrame for stimulation plot data   
    """
    filepath = os.path.join("general_helpers", "common_variables.json")
    with open(filepath, "r") as file:
        common_variables = json.load(file)
    stimulus_length = common_variables['stimulus_length']
    params_sample = np.array([params])
    gwn_stim_data, timed_stimulus = load_simulation_stimulus()
    sim_data = lif_simulation(params_sample, timed_stimulus, stimulus_length=stimulus_length, mv=True)
    baseline, stimulation = seperate_data_incl_membvol(sim_data, gwn_stim_data['baseline_recording'])
    rel_stimulation = relativ_stimulation_times(stimulation, gwn_stim_data['baseline_recording'])

    data = {
        'baseline_time': np.round(baseline['time'][0], 7),
        'baseline_voltage': baseline['membrane_voltage'][0],
        'baseline_spikes': baseline['spikes'][0], 
        'whitenoise_time': np.round(rel_stimulation['time'][0], 7),
        'whitenoise_spikes': np.array(rel_stimulation['spikes'][0], dtype=object),  
        'parameters': params,  
    }
    baseparams, baseplot = sim_baseline_data(baseline)
    gwnparams, stimplot = sim_gwn_data(rel_stimulation, gwn_stim_data)
    features = np.array(baseparams + gwnparams)
    return SimulationResult(
        data=data,
        features=features,
        baseplot=baseplot,
        stimplot=stimplot
    )



def create_cell_from_input_features(features):
    """
    Get MAP model for a single set of cell features

    For a set of cell features from the user, use sbi to compute a MAP model by drawing models from a posterior.

    Parameters
    ----------
    features : list (?)
        feature set attention!: order in "human logical" order! reorder into sbi training order
    
    Returns
    -------
    parameter : np.array
        model parameter set       
    """
    # load stuff you need for simulation analysis
    filepath = os.path.join("general_helpers", "new_order.json")
    with open(filepath, "r") as file:
        new_order = json.load(file)['new_order']
    file.close()
    filepath = os.path.join("..", "source", "posterior.pkl")
    with open(filepath, 'rb') as handle:
        posterior = pickle.load(handle)
    handle.close()
    wanted_cell = np.array(features)
    back_to_original = np.argsort(new_order)
    rel_stats = wanted_cell[back_to_original]
    # get MAP model
    p = posterior.set_default_x(rel_stats) 
    mapped_posterior = p.map(num_iter=1000, show_progress_bars=False)
    parameter = mapped_posterior.tolist()[0]
    return parameter
    




def get_subset_values(sum_stats, prior_samples, values, n):

    if n > len(sum_stats): 
        raise ValueError(f"Error: wanted number of models {n} surpasses model catalogou size of 12 Mio.")

    dims_to_use = np.where(~np.isnan(values))[0]
    if len(dims_to_use) == 0:
        #print("Warning: no valid choices provided, returning random samples.")
        nearest_idx = np.random.choice(sum_stats.shape[0], size=n, replace=False)
        nearest_sum_stats = sum_stats[nearest_idx]
        nearest_prior_samples = prior_samples[nearest_idx]
    else: 
        # cut down vals and sum stats to relevent dimentions 
        vals_sub = values[dims_to_use]
        sum_stats_sub = sum_stats[:, dims_to_use]
        # best needs to start relly high to be cut off
        best_dist = np.full(n, np.inf, dtype=np.float32)
        best_idx = np.full(n, -1, dtype=np.int64)
        # chunks to be able to run this with less RAM
        chunk_size = 500_000 
        for start in range(0, sum_stats.shape[0], chunk_size):
            stop = min(start + chunk_size, sum_stats.shape[0])
            block = sum_stats_sub[start:stop]
            # distange between wanted an have
            diff = block - vals_sub   
            dist2 = np.einsum('ij,ij->i', diff, diff) # distance without creating a giant temporary
            idx = np.argpartition(dist2, n)[:n]
            cand_dist = dist2[idx]
            cand_idx = idx + start
            # merge with current best
            all_dist = np.concatenate((best_dist, cand_dist))
            all_idx = np.concatenate((best_idx, cand_idx))
            # take n best fitting
            keep = np.argpartition(all_dist, n)[:n] # if same distance, will be 'random-ish' no need for random samples implementation (ask Jan if I am right)
            best_dist = all_dist[keep]
            best_idx = all_idx[keep]
        # final ordering
        order = np.argsort(best_dist)
        nearest_sum_stats = sum_stats[best_idx[order]]
        nearest_prior_samples = prior_samples[best_idx[order]]
    return nearest_sum_stats, nearest_prior_samples







