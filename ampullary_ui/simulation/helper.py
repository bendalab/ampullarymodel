"""
Logic functions for implementing user interactions

- Simulate a neuron from a single set of model parameter
- Get MAP model for a single set of cell features
"""
import pickle
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, Any
from pathlib import Path

from ampullary_ui.simulation.lif_simulation import ampullary_lif
from ampullary_ui.utils import load_gwnstimulus, modify_stimulus, load_new_order
from ampullary_ui.analysis.utils import split_data, spiketimes_to_trials
from ampullary_ui.analysis.baseline import baseline_features, baseline_plot_data
from ampullary_ui.analysis.whitenoise import whitenoise_features, whitenoise_plot_data


@dataclass
class SimulationResult:
    data: Dict[str, Any]               # simulation data dictionary
    stim_data : None                   # stimulus data and metadata
    features: np.ndarray               # analysis output features array
    baseline_data: pd.DataFrame        # DataFrame for baseplot data
    stimulus_data: pd.DataFrame        # DataFrame for stimulation plot data



def simulate_from_input_params(params, baseline_duration=30.,
                               prerun_duration=1.0,
                               stimulus_sd=0.2, trials=10):
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
        simulation data dictionary, analysis output features array, DataFrame
        for baseplot data, DataFrame for stimulation plot data   
    """
    params_sample = np.array([params])

    gwn_stim_data = load_gwnstimulus()
    modified_stimulus = modify_stimulus(gwn_stim_data, baseline_duration, prerun_duration,
                                        trials, stimulus_sd)

    sim_data = ampullary_lif(params_sample, modified_stimulus, prerun_duration, record_voltage=True)
    baseline, stimulation = split_data(sim_data, baseline_duration, gwn_stim_data["duration"])
    rel_stimulation = spiketimes_to_trials(stimulation)

    data = {
        'baseline_time': np.round(baseline['time'][0], 7),
        'baseline_voltage': baseline['membrane_voltage'][0],
        'baseline_spikes': baseline['spikes'][0], 
        'whitenoise_time': np.round(rel_stimulation['time'][0], 7),
        'whitenoise_spikes': np.array(rel_stimulation['spikes'][0], dtype=object),  
        'parameters': params,
    }

    basefeatures = baseline_features(baseline["spikes"], baseline['time'])
    baseplot = baseline_plot_data(baseline)
    noisefeatures = whitenoise_features(rel_stimulation, gwn_stim_data, sigma=0.0025)
    noiseplot = whitenoise_plot_data(rel_stimulation, gwn_stim_data)

    feat_tensor = np.array([basefeatures[k].item() for k in basefeatures] + 
                           [noisefeatures[k].item() for k in noisefeatures])

    results = SimulationResult(data=data, stim_data=gwn_stim_data,
                               features=feat_tensor,
                               baseline_data=baseplot,
                               stimulus_data=noiseplot)

    return results


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
    new_order = load_new_order()
    # from IPython import embed
    # embed()
    # import torch
    path = Path.cwd() / "source" / "posterior.pkl"
    with open(path, 'rb') as handle:
        posterior = pickle.load(handle)
    handle.close()

    wanted_cell = np.array(features)
    back_to_original = np.argsort(new_order)
    rel_stats = wanted_cell[back_to_original]

    p = posterior.set_default_x(rel_stats)
    mapped_posterior = p.map(num_iter=1000, show_progress_bars=False)
    parameter = mapped_posterior.tolist()[0]
    return parameter

