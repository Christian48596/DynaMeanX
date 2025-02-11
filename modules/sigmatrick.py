# modules/sigmatrick.py
"""
Module that computes self-energy and spectral function ("sigmatrick") using
imag/real Green's function data and Delta data. It performs:

1) Reads columns from:
   - c-imG.dat (imag part of G)
   - c-reG.dat (real part of G)
   - c-imF.dat (imag part of F)
   - c-reF.dat (real part of F)
   - Delta.dat (imag part of Delta in column 2)
   - Delta-re.dat (real part of Delta in column 2)

2) For each frequency omega[i]:
   - G = reG[i] + i*imG[i]
   - F = reF[i] + i*imF[i]
   - sigma = F / G
   - delta = redelta[i] + i*imdelta[i]
   - gf = 1.0 / (omega[i] + delta - sigma)
   - A(omega) = -1/pi * Im(gf)

3) Writes:
   - c-self.dat:  omega, A(omega)
   - imsigma.dat: omega, Im(sigma)
   - resigma.dat: omega, Re(sigma)

Usage (called from main.py, not standalone):
    from modules.sigmatrick import execute_sigmatrick, SigmaTrickError
    try:
        execute_sigmatrick()
    except SigmaTrickError as e:
        print(f"Error: {e}")
        sys.exit(1)
"""

import math
import cmath
import os
import sys
import logging

class SigmaTrickError(Exception):
    """Custom exception for errors in sigmatrick.py."""
    pass

# Configure logger for this module
logger = logging.getLogger(__name__)
# Set the logger's level to DEBUG to capture all messages
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    # File handler: capture all logs at DEBUG in 'sigmatrick.log'
    fh = logging.FileHandler('sigmatrick.log')
    fh.setLevel(logging.DEBUG)  # Capture DEBUG and above in the file
    fh_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(fh_formatter)
    logger.addHandler(fh)

    # Console handler: only show INFO+ (i.e., error messages) on console
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)  # Capture INFO and above on console
    ch_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    ch.setFormatter(ch_formatter)
    logger.addHandler(ch)

    # Disable propagation to prevent duplication
    logger.propagate = False

def _readcol(filename, column):
    """
    Reads the specified 1-based column from a text file that typically has two columns.
    Returns a list of floats.
    Logs routine steps at DEBUG, errors at INFO.
    """
    logger.debug(f"Reading column {column} from file '{filename}'...")
    values = []
    try:
        with open(filename, 'r') as f:
            for line_num, line in enumerate(f, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                parts = stripped.split()
                val = float(parts[column - 1])
                values.append(val)
    except FileNotFoundError:
        msg = f"Input file '{filename}' not found."
        logger.info(msg)  # Show error on console
        raise SigmaTrickError(msg)
    except Exception as e:
        msg = f"Error reading '{filename}': {e}"
        logger.info(msg)
        raise SigmaTrickError(msg)

    logger.debug(f"Successfully read {len(values)} values from '{filename}'.")
    return values

def execute_sigmatrick():
    """
    Main function to compute self-energy trick. Writes c-self.dat, imsigma.dat, resigma.dat.
    Logs routine steps at DEBUG and any errors at INFO.
    Raises SigmaTrickError on failure.
    """
    logger.debug("Starting execute_sigmatrick().")

    try:
        # 1) Read input columns
        omega     = _readcol("c-imG.dat", 1)
        imG       = _readcol("c-imG.dat", 2)
        reG       = _readcol("c-reG.dat", 2)
        imF       = _readcol("c-imF.dat", 2)
        reF       = _readcol("c-reF.dat", 2)
        imdelta   = _readcol("Delta.dat",    2)
        redelta   = _readcol("Delta-re.dat", 2)
    except SigmaTrickError as e:
        # Already logged at INFO
        raise e

    # 2) Prepare output files
    selffn  = "c-self.dat"
    imsigma = "imsigma.dat"
    resigma = "resigma.dat"
    logger.debug(f"Output files: {selffn}, {imsigma}, {resigma}")

    try:
        f_self = open(selffn,  "w")
        f_im   = open(imsigma, "w")
        f_re   = open(resigma, "w")
    except Exception as e:
        msg = f"Error opening output files: {e}"
        logger.info(msg)
        raise SigmaTrickError(msg)

    # 3) Check data lengths
    length = len(omega)
    if any(length != len(arr) for arr in (imG, reG, imF, reF, imdelta, redelta)):
        msg = "Mismatch in data lengths among the input files."
        logger.info(msg)
        raise SigmaTrickError(msg)

    logger.debug(f"Processing {length} frequency points.")
    for i in range(length):
        o     = omega[i]
        G     = complex(reG[i], imG[i])
        F     = complex(reF[i], imF[i])
        delta = complex(redelta[i], imdelta[i])

        # sigma = F / G, handle G ~ 0
        if abs(G) < 1e-30:
            msg = f"Warning: G ~ 0 at index {i}, omega={o}. Using sigma=0."
            logger.info(msg)
            sigma = 0+0j
        else:
            sigma = F / G

        # gf = 1/(omega + delta - sigma), handle near-zero denominator
        denom = complex(o, 0) + delta - sigma
        if abs(denom) < 1e-30:
            msg = f"Warning: denominator near zero at index {i}, omega={o}. Skipping."
            logger.info(msg)
            continue

        gf = 1.0 / denom
        aw = -1.0 / math.pi * gf.imag

        f_self.write(f"{o} {aw}\n")
        f_im.write(f"{o} {sigma.imag}\n")
        f_re.write(f"{o} {sigma.real}\n")

    f_self.close()
    f_im.close()
    f_re.close()

    logger.debug("execute_sigmatrick() completed with no errors, outputs written.")