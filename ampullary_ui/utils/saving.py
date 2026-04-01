"""
All the saving functions for the different results, formats etc. 
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
import logging
import pandas as pd
import numpy as np

from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QFileDialog

from . import load_labels


labels = load_labels()
parameter_labels = labels['parameter_save_labels']
feature_labels = labels['feature_save_labels']

def read_output_folder():
    settings = QSettings()
    output_folder = settings.value("app/output_folder", str(Path.cwd()))
    return output_folder

def store_output_folder(output_folder):
    settings = QSettings()
    settings.setValue("app/output_folder", str(output_folder))

def get_outputfolder():
    output_folder = read_output_folder()
    output_folder = QFileDialog.getExistingDirectory(None, "Select output folder",
                                                         dir=output_folder)
    if not output_folder:
        logging.info("Folder selection cancelled")
        return None
    output_folder = Path(output_folder)
    store_output_folder(output_folder)

    return output_folder

def ensure_folder(output_folder):
    output_folder.mkdir(parents=True, exist_ok=True)
    return output_folder

def save_data(data, folder, filename):
    """
    Save simulation data dictionary as npz
    save on pre-directed path

    Parameters:
    -----------
    data : dict
        simulation data dictionary, incl simulated voltage for baseline
    folder : pathlib.Path
        the parent output folder
    filename : str
        filename, user input

    Returns:
    -------
    None
    """
    output_dir = ensure_folder(folder / "derived_data" / "simulations")
    logging.debug("Saving data to %s", output_dir)
    np.savez(output_dir / f"simulation_data_{filename}.npz", **data)


def save_params(params, folder, filename):
    """
    convert single parameter set into one line Dataframe and save
    save on pre-directed path

    Parameters:
    -----------
    params : np.array
        model parameter set
    folder : pathlib.Path
        the parent output folder
    filename : str
        filename, user input

    Returns:
    -------
    None
    """
    output_dir =  ensure_folder(folder / "derived_data" / "parameter")
    d = {'name' : filename}  
    for i in range(len(params)):
        d[parameter_labels[i]] = float(params[i])
    df = pd.DataFrame(d, index=[0])
    logging.debug("Saving paramters to %s", output_dir)
    df.to_csv(output_dir / f"parameter_{filename}.csv", index = False) 


def save_features(features, folder, filename):
    """
    convert single feature set into one line Dataframe and save
    save on pre-directed path
    
    Parameters:
    -----------
    features : np.array
        feature set
    folder : pathlib.Path
        the parent output folder
    filename : str
        filename, user input

    Returns:
    -------
    None
    """
    output_dir = ensure_folder(folder / "derived_data" / "parameter")

    d = {'name' : filename}  
    for i in range(len(features)):
        d[feature_labels[i]] = float(features[i])
    df = pd.DataFrame(d, index=[0])
    logging.debug("Saving features to %s", output_dir)
    df.to_csv(output_dir / f"features_{filename}.csv", index = False) 


def save_figure(fig, folder: Path, filename: str):
    """
    Save a figure
    save on pre-directed path

    Parameters:
    -----------
    fig : matplotlib figure
    folder : pathlib.Path
        the parent output folder
    filename : pathlib.Path
        the desired filename

    Returns:
    -------
    None
    """
    output_dir = ensure_folder(folder / "derived_data" / "figures")
    logging.debug(f"Saving figure {filename} to {output_dir}")
    fig.savefig(output_dir / f"cell_simulation_{filename}")


def save_sampled_subset(feature_samples, prior_samples, output_folder, filename):
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
    output_folder : Path
        the output parent path
    filename : str
        filename, user input
    
    Returns:
    -------
    None
    """
    output_dir = ensure_folder(output_folder / "derived_data" / "subsets")

    df_sum_subset_samples = pd.DataFrame(data =  feature_samples, columns = feature_labels)
    df_sum_subset_samples.to_csv(output_dir / f"feature_sample_subset_{filename}.csv", index = False)
    df_prior_subset_samples = pd.DataFrame(data = prior_samples, columns = parameter_labels)
    df_prior_subset_samples.to_csv(output_dir / f"prior_sample_subset_{filename}.csv", index = False)


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


def save_features_table(collect_features, output_folder, filename):
    """
    convert multiple feature sets into Dataframe and save
    
    Parameters:
    -----------
    collect_features : np.array
        arrays of multiple feature sets
    output_folder : pathlib.Path
        Directory path where feature sets will be stored
    filename : str
        filename, user input

    Returns:
    -------
    None
    """
    output_dir = ensure_folder(output_folder)
    df = pd.DataFrame(data = collect_features, columns = feature_labels)
    filepath = output_dir / f"{filename}_feature_table.csv"
    df.to_csv(filepath, index = False)
