# modules/broyden.py
"""
Broyden Mixing Module

Implements the Broyden mixing method to assist in self-energy convergence.

Logging:
   - All routine steps are logged at DEBUG into 'Broyden.log'.
   - Only INFO-level messages (errors and warnings) are displayed on the console.
"""

import logging
import numpy as np

class BroydenMixingError(Exception):
    """Custom exception for errors in broyden.py."""
    pass

def apply_broyden_mixing(old_delta, new_delta, mixing_parameter=0.1):
    """
    Applies Broyden mixing to update Delta.dat.

    Args:
        old_delta (numpy.ndarray): Previous Delta values.
        new_delta (numpy.ndarray): Newly computed Delta values.
        mixing_parameter (float): Mixing parameter alpha (0 < alpha <= 1).

    Returns:
        numpy.ndarray: Updated Delta values after mixing.

    Raises:
        BroydenMixingError: If inputs are invalid or mixing fails.
    """
    # Initialize logger inside the function
    logger = logging.getLogger('broyden')
    if not logger.handlers:
        # File Handler captures all logs (DEBUG+) in Broyden.log
        fh = logging.FileHandler('broyden.log')
        fh.setLevel(logging.DEBUG)  # Capture DEBUG and above in the file
        fh_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        fh.setFormatter(fh_formatter)
        logger.addHandler(fh)

        # Console Handler only shows INFO+ (i.e., errors)
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)  # Capture INFO and above on console
        ch_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        ch.setFormatter(ch_formatter)
        logger.addHandler(ch)

        # Disable propagation to prevent duplication
        logger.propagate = False

    logger.debug("Starting Broyden mixing.")
    try:
        if old_delta is None:
            logger.debug("No previous Delta found. Using new Delta without mixing.")
            return new_delta

        if not (0 < mixing_parameter <= 1):
            msg = f"Invalid mixing parameter: {mixing_parameter}. Must be between 0 and 1."
            logger.info(msg)
            raise BroydenMixingError(msg)

        logger.debug(f"Mixing parameter: {mixing_parameter}")

        # Placeholder for Broyden's method. A full implementation would require storing history.
        # Here, we'll perform a simple linear mixing as a placeholder.

        mixed_delta = mixing_parameter * new_delta + (1 - mixing_parameter) * old_delta
        logger.debug("Broyden mixing applied successfully.")

        return mixed_delta

    except Exception as e:
        msg = f"Error during Broyden mixing: {e}"
        logger.info(msg)
        raise BroydenMixingError(msg)