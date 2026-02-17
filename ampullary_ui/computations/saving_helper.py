"""
All the saving functions for the different rresults, formats etc. 
(except save data in subprocess, thats with table_convert)

- Save simulation data dictionary as npz
- convert single parameter set into one line Dataframe and save
- convert single feature set into one line Dataframe and save
- Save a figure
- Save the sampled subset form catalogue
- convert multiple parameter sets into Dataframe and save
- convert multiple feature sets into Dataframe and save
"""
import os
import pandas as pd
import numpy as np

from ampullary_ui.utils import load_labels


labels = load_labels()
parameter_labels = labels['parameter_save_labels']
feature_labels = labels['feature_save_labels']


def save_data(data, filename):
    """
    Save simulation data dictionary as npz
    save on pre-directed path
    
    Parameters:
    -----------
    data : dict
        simulation data dictionary, incl simulated voltage for baseline
    filename : str
        filename, user input
    
    Returns:
    -------
    None
    """
    output_dir =  os.path.join("..", "derived_data", "simulations")
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, f"simulation_data_{filename}.npz")
    np.savez(filepath, **data)


def save_params(params, filename):
    """
    convert single parameter set into one line Dataframe and save
    save on pre-directed path
    
    Parameters:
    -----------
    params : np.array
        model parameter set
    filename : str
        filename, user input
    
    Returns:
    -------
    None
    """
    output_dir =  os.path.join("..", "derived_data", "parameter")
    os.makedirs(output_dir, exist_ok=True)
    d = {'name' : filename}  
    for i in range(len(params)):
        d[parameter_labels[i]] = float(params[i])
    df = pd.DataFrame(d, index=[0])
    filepath = os.path.join(output_dir, f"parameter_{filename}.csv")
    df.to_csv(filepath, index = False) 


def save_features(features, filename):
    """
    convert single feature set into one line Dataframe and save
    save on pre-directed path
    
    Parameters:
    -----------
    features : np.array
        feature set
    filename : str
        filename, user input

    Returns:
    -------
    None
    """
    output_dir =  os.path.join("..", "derived_data", "features")
    os.makedirs(output_dir, exist_ok=True)
    d = {'name' : filename}  
    for i in range(len(features)):
        d[feature_labels[i]] = float(features[i])
    df = pd.DataFrame(d, index=[0])
    filepath = os.path.join(output_dir, f"features_{filename}.csv")
    df.to_csv(filepath, index = False) 
    

def save_figure(fig, filename):
    """
    Save a figure
    save on pre-directed path
    
    Parameters:
    -----------
    fig : matplotlib figure
    filename : str
        filename, user input
    
    Returns:
    -------
    None
    """
    output_dir =  os.path.join("..", "figures")
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, f"cell_simulation_{filename}")
    fig.savefig(filepath)


def save_sampled_subset(feature_samples, prior_samples, filename):
    """
    Save the sampled subset from catalogue
    save chosen/sampled feature subset and corresponding model parameters
    save on pre-directed path
    
    Parameters:
    -----------
    feature_samples : np.array
        array of arrays of feature sets 
    prior_samples : np.array
        array of arrays of model parameter sets 
    filename : str
        filename, user input
    
    Returns:
    -------
    None
    """
    output_dir = os.path.join( "..", "derived_data", "subsets") 
    os.makedirs(output_dir, exist_ok=True)
    df_sum_subset_samples = pd.DataFrame(data =  feature_samples, columns = feature_labels)
    filepath = os.path.join(output_dir, f"feature_sample_subset_{filename}.csv")
    df_sum_subset_samples.to_csv(filepath, index = False) 
    df_prior_subset_samples = pd.DataFrame(data = prior_samples, columns = parameter_labels)
    filepath = os.path.join(output_dir, f"prior_sample_subset_{filename}.csv")
    df_prior_subset_samples.to_csv(filepath, index = False) 
    

def save_parameter_table(collect_params, output_dir, filename):
    """
    convert multiple parameter sets into Dataframe and save
    
    Parameters:
    -----------
    collect_params : np.array
        arrays of multiple model parameter sets
    output_dir : str
        Directory path where parameter sets will be stored
    filename : str
        filename, user input

    Returns:
    -------
    None
    """
    df = pd.DataFrame(data = collect_params,columns = parameter_labels)
    filepath = os.path.join(output_dir, f"{filename}_parameter_table.csv")
    df.to_csv(filepath, index = False)  


def save_features_table(collect_features, output_dir, filename):
    """
    convert multiple feature sets into Dataframe and save
    
    Parameters:
    -----------
    collect_features : np.array
        arrays of multiple feature sets
    output_dir : str
        Directory path where feature sets will be stored
    filename : str
        filename, user input
    
    Returns:
    -------
    None
    """
    df = pd.DataFrame(data = collect_features,columns = feature_labels)
    filepath = os.path.join(output_dir, f"{filename}_feature_table.csv")
    df.to_csv(filepath, index = False)  