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
