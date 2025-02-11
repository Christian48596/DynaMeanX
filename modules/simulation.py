# modules/simulation.py

import subprocess
import os
import sys
import logging
import time
from shutil import which
from .parameter_parser import get_parameters  # Ensure this module exists and is correctly implemented
import argparse

class SimulationError(Exception):
    """Custom exception for simulation errors."""
    pass

# Configure logging for simulation.py
logger = logging.getLogger(__name__)

# We'll set the base logger level to DEBUG so everything is recorded
logger.setLevel(logging.DEBUG)

# Create handlers if they don't exist to avoid duplicate logs
if not logger.handlers:
    # File handler: capture all logs at DEBUG level into 'simulation.log'
    fh = logging.FileHandler('simulation.log')
    fh.setLevel(logging.DEBUG)
    fh_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(fh_formatter)
    logger.addHandler(fh)

    # Console handler: show only INFO and above on the console
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    ch.setFormatter(ch_formatter)
    logger.addHandler(ch)

    # **Disable propagation to prevent duplication**
    logger.propagate = False

def verify_command(command_name):
    """
    Verifies if a command exists in the system's PATH.
    """
    # We'll do these checks at DEBUG, so they don't appear in console under normal circumstances
    logger.debug(f"Verifying command: {command_name}")
    if which(command_name) is None:
        # If not found, that is an error => show at INFO so user sees it
        logger.info(f"Command not found: {command_name}")
        raise SimulationError(f"Command not found: {command_name}")
    else:
        logger.debug(f"Command '{command_name}' found.")

def generate_param(z, output_dir, param_filename='param'):
    """
    Generates the 'param' configuration file for a specific z-step.
    """
    try:
        # We'll log routine details at DEBUG
        logger.debug(f"Generating param file for z={z} in {output_dir}")

        # Absolute paths for dos and model
        dos_abs_path = os.path.abspath(os.path.join(output_dir, '..', 'Delta.dat'))
        model_abs_path = os.path.abspath(os.path.join(output_dir, '..', 'model.m'))

        # The param file content
        param_content = f"""[extra]
U=2
epsilon=-1

[param]
symtype=QS
Lambda=3
Tmin=1e-8
keepmin=200
keepenergy=8.0
keep=10000

band=asymode
dos={dos_abs_path}
bandrescale=10

discretization=Z

model={model_abs_path}

ops=A_d self_d n_d
specd=A_d-A_d self_d-A_d

fdm=true

broaden_max=10
broaden_ratio=1.01
broaden_min=1e-6
broaden_alpha=0.4
broaden_gamma=0.2
bins=300
broaden=false
savebins=true

T=1e-8

z={z}
"""

        os.makedirs(output_dir, exist_ok=True)
        param_path = os.path.join(output_dir, param_filename)

        with open(param_path, 'w') as param_file:
            param_file.write(param_content)

        # We'll keep this message at DEBUG, so it doesn't clutter the console
        logger.debug(f"Generated param file at: {param_path}")
        return param_path
    except Exception as e:
        # If an error occurs, we show it at INFO so user sees it in console
        logger.info(f"Error generating param file for z={z}: {e}")
        raise SimulationError(f"Error generating param file for z={z}: {e}")

def execute_command(command, description, cwd, verbose=False, retries=3, delay=5, use_mpi=False):
    """
    Executes a shell command with optional MPI, using a retry mechanism.
    """
    if use_mpi:
        mpi_command = ['/opt/homebrew/bin/mpirun', '-np', '4'] + command
    else:
        mpi_command = command

    full_command = ' '.join(mpi_command)
    for attempt in range(1, retries + 1):
        logger.debug(f"Attempt {attempt}: {description} => {full_command}")
        try:
            result = subprocess.run(
                mpi_command, 
                check=True, 
                cwd=cwd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True
            )
            logger.debug(f"Successfully executed '{description}' in '{cwd}'.")
            if verbose:
                logger.debug(f"STDOUT:\n{result.stdout}")
                logger.debug(f"STDERR:\n{result.stderr}")
            return  # success => exit function
        except subprocess.CalledProcessError as e:
            # It's an error => log at INFO so user sees it
            logger.info(f"Attempt {attempt} failed for '{description}' in '{cwd}': {e.stderr}")
            if attempt < retries:
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                logger.info(f"All {retries} attempts failed for '{description}' in '{cwd}'.")
                raise SimulationError(f"All {retries} attempts failed for '{description}' in '{cwd}'.")

def validate_files(param_file_path, simulation_dir):
    """
    Validates the existence of required files before running simulations.
    """
    logger.debug(f"Validating param file: {param_file_path} in {simulation_dir}")
    try:
        with open(param_file_path, 'r') as param_file:
            lines = param_file.readlines()
            dos_line = next((line for line in lines if line.startswith("dos=")), None)
            model_line = next((line for line in lines if line.startswith("model=")), None)
            
            dos_path = dos_line.split("=",1)[1].strip() if dos_line else None
            model_path = model_line.split("=",1)[1].strip() if model_line else None
            
            missing_files = []
            if dos_path:
                if not os.path.isfile(dos_path):
                    missing_files.append(dos_path)
            else:
                logger.info("Parameter 'dos' is missing in param file.")
                raise SimulationError("Parameter 'dos' is missing in param file.")
            
            if model_path:
                if not os.path.isfile(model_path):
                    missing_files.append(model_path)
            else:
                logger.info("Parameter 'model' is missing in param file.")
                raise SimulationError("Parameter 'model' is missing in param file.")
            
            if missing_files:
                for file in missing_files:
                    logger.info(f"Required file not found: {file}")
                raise SimulationError("One or more required files are missing.")
    except SimulationError:
        raise
    except Exception as e:
        logger.info(f"Error validating files: {e}")
        raise SimulationError(f"Error validating files: {e}")

def run_simulation(z, simulation_dir, params, verbose=False):
    """
    Runs a single simulation for a given z-step.
    """
    try:
        # We'll show these lines at INFO => user sees them if all is well
        logger.info(f"--- Processing z = {z} in directory {simulation_dir} ---")

        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        simulation_path = os.path.join(project_root, simulation_dir)
        os.makedirs(simulation_path, exist_ok=True)
        logger.debug(f"Output directory '{simulation_dir}' created at '{simulation_path}'")
        
        param_file = generate_param(z, simulation_path)
        validate_files(param_file, simulation_path)
        
        verify_command('nrginit')
        verify_command('nrg')
        
        # nrginit (no MPI)
        execute_command(['nrginit'], f"nrginit for z={z}", cwd=simulation_path, verbose=verbose, use_mpi=False)
        
        # nrg (with MPI)
        execute_command(['nrg'], f"nrg for z={z}", cwd=simulation_path, verbose=verbose, use_mpi=True)
        
        dir_contents = os.listdir(simulation_path)
        logger.debug(f"Contents of {simulation_dir}: {dir_contents}")
        
        # This line is also at INFO => user sees it for success
        logger.info(f"--- Completed z = {z} in directory {simulation_dir} ---\n")

    except SimulationError as e:
        # If there's a simulation-level error, we log at INFO => user sees it
        logger.info(f"Simulation error during simulation for z={z}: {e}")
    except Exception as e:
        # Unexpected error => also log at INFO
        logger.info(f"Unexpected error during simulation for z={z}: {e}")
        # Continue with other simulations

def run_all_simulations(params, verbose=False):
    """
    Runs all simulations sequentially based on the defined z-steps.
    """
    Nz = params.get("Nz", 4)  # default to 4 if not specified
    
    step_size = 1.0 / Nz
    z_values = [round(step_size * (i + 1), 8) for i in range(Nz)]
    
    # We'll show this line at INFO => if it goes right, user sees only this line
    logger.info("Starting simulations sequentially.")
    logger.debug(f"z values to process: {z_values}")

    for index, z in enumerate(z_values, start=1):
        simulation_dir = str(index)
        run_simulation(z, simulation_dir, params, verbose=verbose)