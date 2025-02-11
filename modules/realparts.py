# modules/realparts.py
"""
A Python module to compute real parts of Green's functions from imaginary parts
(c-imF.dat, c-imG.dat) via the "kk" executable.
All routine steps are logged at DEBUG into realparts.log. 
Only INFO-level messages (errors) are displayed on the console.
"""

import os
import sys
import subprocess
import logging

class RealPartsError(Exception):
    """Custom exception for realparts.py errors."""
    pass

# Configure the logger for this module
logger = logging.getLogger(__name__)

# Set the logger's level to DEBUG to capture all messages
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    # File Handler: Record DEBUG and above in 'realparts.log'
    fh = logging.FileHandler('realparts.log')
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

    # Disable propagation to prevent duplication
    logger.propagate = False

def execute_realparts():
    """
    Calls 'kk' on each of 'c-imF.dat' and 'c-imG.dat', generating 'c-reF.dat' and 'c-reG.dat'.
    Assumes:
      - 'kk' is installed and in system PATH
      - 'c-imF.dat' and 'c-imG.dat' are in current directory

    Raises:
      RealPartsError: If input files are missing, 'kk' fails, or output files are not created.
    """
    logger.debug("Starting real-parts computation (execute_realparts).")

    # We'll look for 'c-imF.dat' and 'c-imG.dat' in current dir
    file_prefixes = ["c-imF", "c-imG"]
    kkexe = "kk"  # Command to run

    for prefix in file_prefixes:
        in_file = f"{prefix}.dat"            # e.g. "c-imF.dat"
        out_file = in_file.replace("im", "re")  # e.g. "c-reF.dat"

        # Check existence of input
        if not os.path.isfile(in_file):
            msg = f"Input file '{in_file}' not found."
            logger.info(msg)  # Show at console
            raise RealPartsError(msg)

        cmd = f"{kkexe} {in_file} {out_file}"
        logger.debug(f"Executing command: {cmd}")

        try:
            subprocess.check_call(cmd, shell=True)
        except subprocess.CalledProcessError as e:
            msg = f"Command '{cmd}' failed: {e}"
            logger.info(msg)
            raise RealPartsError(msg)

        # Verify output
        if not os.path.isfile(out_file):
            msg = f"Output file '{out_file}' not found after running '{cmd}'."
            logger.info(msg)
            raise RealPartsError(msg)

        logger.debug(f"Successfully created '{out_file}' from '{in_file}'.")

    logger.debug("execute_realparts() completed with no errors.")