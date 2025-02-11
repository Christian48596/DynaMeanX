# modules/average.py

import os
import sys
import re
import logging
import subprocess
import shutil
from datetime import datetime

class AverageModuleError(Exception):
    """Custom exception for errors in average.py."""
    pass

# Configure logging for average.py
logger = logging.getLogger(__name__)

# Set the logger's level to DEBUG to capture all messages
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    # File Handler: Record DEBUG and above in 'average.log'
    fh = logging.FileHandler('average.log')
    fh.setLevel(logging.DEBUG)
    fh_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(fh_formatter)
    logger.addHandler(fh)

    # Console Handler: Display only INFO and above in the console
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    ch.setFormatter(ch_formatter)
    logger.addHandler(ch)

    # **Disable propagation to prevent duplication**
    logger.propagate = False

def parse_param_loop(filepath):
    """
    Parses the param.loop file to extract parameters, including #PRELUDE variables.

    Returns:
        dict: A dictionary of parsed parameters.

    Raises:
        AverageModuleError: If file is missing or a key parameter is missing.
    """
    # Log routine steps at DEBUG so they don't appear if everything is fine
    logger.debug(f"Parsing param.loop from: {filepath}")

    params = {}
    prelude_pattern = re.compile(r'^#PRELUDE:\s*(.*)')
    variable_pattern = re.compile(r'\$(\w+)\s*=\s*([^;]+);?')
    param_pattern = re.compile(r'(\w+)\s*=\s*(.+)')
    section = None

    if not os.path.isfile(filepath):
        msg = f"File '{filepath}' not found."
        # Log at INFO so user sees it
        logger.info(msg)
        raise AverageModuleError(msg)

    try:
        with open(filepath, 'r') as file:
            for line_number, line in enumerate(file, 1):
                stripped_line = line.strip()
                logger.debug(f"Line {line_number}: {stripped_line}")

                prelude_match = prelude_pattern.match(stripped_line)
                if prelude_match:
                    prelude_content = prelude_match.group(1)
                    logger.debug(f"Found PRELUDE content: '{prelude_content}'")
                    for var_match in variable_pattern.finditer(prelude_content):
                        key, value = var_match.groups()
                        params[key.strip()] = value.strip()
                        logger.debug(f"Found PRELUDE variable '{key}' = '{value}'")
                    continue

                if not stripped_line or stripped_line.startswith("#"):
                    continue

                if stripped_line.startswith("["):
                    section = stripped_line.strip("[]").lower()
                    logger.debug(f"Entering section [{section}]")
                    continue

                if section in ["extra", "param"]:
                    param_match = param_pattern.match(stripped_line)
                    if param_match:
                        key, value = param_match.groups()
                        params[key.strip()] = value.strip()
                        logger.debug(f"Found parameter '{key}' = '{value}'")

        if 'Nz' not in params:
            msg = "Missing 'Nz' parameter in param.loop."
            logger.info(msg)
            raise AverageModuleError(msg)

        params['Nz'] = int(params['Nz'])
        logger.debug(f"Converted 'Nz' to integer: {params['Nz']}")
        return params

    except AverageModuleError:
        raise
    except Exception as e:
        msg = f"Error reading '{filepath}': {e}"
        logger.info(msg)
        raise AverageModuleError(msg)

def broaden_command(fn, out, params, broaden_exec="broaden"):
    """
    Executes 'broaden' at the top-level directory. 'broaden' internally handles 1/, 2/, etc.
    """
    cmd = (
        f"{broaden_exec} "
        f"-x {params['broaden_gamma']} "
        f"-m {params['broaden_min']} "
        f"-M {params['broaden_max']} "
        f"-r {params['broaden_ratio']} "
        f"{fn} {params['Nz']} {params['broaden_alpha']} {params['T']} 1e-99"
    )

    # Log at DEBUG
    logger.debug(f"Executing command: {cmd}")

    try:
        process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=os.environ.copy()  # Using current environment without modifying DYLD_LIBRARY_PATH
        )

        # Log each line at DEBUG for normal operation
        for line in process.stdout:
            logger.debug(line.strip())

        process.wait()
        if process.returncode != 0:
            msg = f"Command '{cmd}' exited with return code {process.returncode}"
            logger.info(msg)  # Log error at INFO
            raise AverageModuleError(msg)
        else:
            # Successful => keep at DEBUG
            logger.debug(f"Command '{cmd}' completed successfully.")
    except Exception as e:
        msg = f"Unexpected error running '{cmd}': {e}"
        logger.info(msg)
        raise AverageModuleError(msg)

    # Move spec.dat -> out
    if not os.path.exists("spec.dat"):
        msg = "spec.dat was not generated by the broaden command."
        logger.info(msg)
        raise AverageModuleError(msg)

    try:
        shutil.move("spec.dat", out)
        logger.debug(f"Moved 'spec.dat' to '{out}'")
    except Exception as e:
        msg = f"Error moving 'spec.dat': {e}"
        logger.info(msg)
        raise AverageModuleError(msg)

def execute_average():
    """
    Main entry point for averaging operation. 
    """
    # Log at DEBUG
    logger.debug("Starting average processing...")

    param_loop_path = "param.loop"
    if not os.path.isfile(param_loop_path):
        msg = f"'{param_loop_path}' does not exist."
        logger.info(msg)
        raise AverageModuleError(msg)

    params = parse_param_loop(param_loop_path)
    params.setdefault('broaden_gamma', 0.2)
    params.setdefault('broaden_alpha', 0.4)
    params.setdefault('T', 1e-8)

    pr = "FDM_dens"
    files_to_process = [
        (f"spec_{pr}_A_d-A_d.bin", "c-imG.dat"),
        (f"spec_{pr}_self_d-A_d.bin", "c-imF.dat")
    ]

    logger.debug(f"Files to process: {files_to_process}")
    logger.debug("Executing 'broaden_command' for each file...")

    for fn, out in files_to_process:
        logger.debug(f"Processing file: {fn} -> {out}")
        broaden_command(fn, out, params)

    logger.debug("All averaging steps completed successfully.")